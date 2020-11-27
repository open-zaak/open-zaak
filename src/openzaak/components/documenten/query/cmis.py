# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import copy
import datetime
import logging
import uuid
from itertools import groupby
from operator import attrgetter, itemgetter
from typing import List, Optional, Tuple

from django.db import IntegrityError
from django.db.models import fields
from django.db.models.query import BaseIterable
from django.forms.models import model_to_dict
from django.utils import timezone

from django_loose_fk.virtual_models import ProxyMixin
from drc_cmis.utils import exceptions
from drc_cmis.utils.convert import make_absolute_uri
from drc_cmis.utils.mapper import mapper
from rest_framework.request import Request
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.utils.mixins import CMISClientMixin

from ...catalogi.models.informatieobjecttype import InformatieObjectType
from ..utils import Cmisdoc, CMISStorageFile
from .django import (
    InformatieobjectQuerySet,
    InformatieobjectRelatedQuerySet,
    ObjectInformatieObjectQuerySet,
)

logger = logging.getLogger(__name__)


# map query names from django models to properties on the CMIS models
EIO_PROPERTY_MAP = {
    "canonical": "uuid",  # UUID is the same for different versions
    "versie": "versie",
}


def sort_results(documents: List, order_by: List[str]) -> List:
    # mixing ASC/DESC is not possible in a single sorted(...) call with the `reverse`
    # option, so we need to call sorted for every order key, and do this in reverse.
    # if the order key starts with `-` to indicate DESC sorting, we need to reverse
    for order_key in order_by[::-1]:
        reverse = order_key.startswith("-")
        _order_key = order_key if not reverse else order_key[1:]
        documents = sorted(
            documents, key=attrgetter(EIO_PROPERTY_MAP[_order_key]), reverse=reverse
        )
    return documents


# ---------------------- Model iterables -----------

# TODO Refactor so that all these iterables inherit from a class that implements the shared functionality
class CMISDocumentIterable(BaseIterable, CMISClientMixin):

    table = "drc:document"
    return_type = "Document"

    def __iter__(self):
        queryset = self.queryset

        filters = self._check_for_pk_filter(queryset._cmis_query)

        lhs, rhs = self._normalize_filters(filters)

        documents = queryset.cmis_client.query(self.return_type, lhs, rhs)
        documents = self._process_intermediate(queryset.query, documents)

        version = dict(filters).get("versie")
        begin_registratie = dict(filters).get("begin_registratie")

        if self._needs_vertrowelijkaanduiding_filter(filters):
            documents = self._filter_by_va(filters, documents)

        # a collection of (uuid, versie) which is considered unique together. Once such
        # a tuple is seen, no extra results with the same version can be seen. This is
        # required because alfresco tracks cmis:versionLabel for all updates, while they
        # keep the same Documenten API versie (i.e.: there are multiple alfresco versions
        # with the (uuid, versie) combo).
        uuid_version_tuples_seen = set()

        for document in documents:
            # distinct on canonical -> we want the latest version of each document, if
            # a PWC exists, grab that. This means -> don't fetch additional versions
            if "canonical" in queryset.query.distinct_fields:
                assert (
                    "-versie" in queryset.query.order_by
                ), "Undefined behaviour w/r to version sorting"
                eio = cmis_doc_to_django_model(
                    document,
                    skip_pwc=False,
                    version=version,
                    begin_registratie=begin_registratie,
                )
                yield eio

            # general query, we want multiple versions of the same document -> get the entire
            # version history
            else:
                versions = self.cmis_client.get_all_versions(document)
                versions = sort_results(versions, queryset.query.order_by)

                seen = set()
                for version in versions:
                    if version.versie in seen:
                        continue

                    uuid_version_combination = (version.uuid, version.versie)
                    if uuid_version_combination in uuid_version_tuples_seen:
                        continue

                    # mark version as seen in both scopes
                    seen.add(version.versie)
                    uuid_version_tuples_seen.add(uuid_version_combination)

                    yield cmis_doc_to_django_model(version, skip_pwc=True)

    def _process_intermediate(
        self, django_query, documents: List[Cmisdoc]
    ) -> List[Cmisdoc]:
        """
        Order the results of the CMIS query and throw out non-distinct results.
        """
        _order_keys = [
            key if not key.startswith("-") else key[1:] for key in django_query.order_by
        ]
        if any(key not in EIO_PROPERTY_MAP for key in _order_keys):
            raise NotImplementedError(
                f"Not all order keys in {_order_keys} are implemented yet."
            )

        documents = sort_results(documents, django_query.order_by)

        if django_query.distinct and not django_query.distinct_fields:
            raise NotImplementedError("Blank distinct not implemented.")

        # now that the ordering is okay, implement the distinct fields
        for field in django_query.distinct_fields:
            attr_name = EIO_PROPERTY_MAP[field]
            to_keep = []
            seen = set()
            # loop over the sorted documents, and grab the first un-seen record for this
            # particular distinct field
            for document in documents:
                value = getattr(document, attr_name)
                # value already seen -> skip subsequent ones
                if value in seen:
                    continue

                # first occurrence - keep the document and mark the value as seen
                to_keep.append(document)
                seen.add(value)

            # re-assign the result set of documents to only those to keep, and repeat
            # for remaining distinct fields
            documents = to_keep

        # do a final sort, because UUID sorting (canonical) does not mimic reality
        if _order_keys and _order_keys[0] == "canonical":
            grouped = []
            # maintain any groups that may have been bundled by UUID! and then sort the
            # groups
            for canonical, group in groupby(documents, key=attrgetter("uuid")):
                group = list(group)
                min_creation = min([x.creationDate for x in group])
                grouped.append((min_creation, group))

            # now the groups are sorted by their logical canonical creation date
            grouped = sorted(grouped, key=itemgetter(0))
            # merge the documents together again (flattening the tuples of [int, list])
            documents = sum([group for _, group in grouped], [])

        return documents

    def _normalize_filters(self, filters: List[Tuple]) -> Tuple[List[str], List[str]]:
        """
        Normalize the various flavours of ORM filters.

        Turn dict filters into something that looks like SQL 92 suitable for Alfresco
        CMIS query. Note that all filters are AND-ed together.

        Ideally, this would be an implementation of the as_sql for a custom database
        backend, returning lhs and rhs parts.
        """
        _lhs = []
        _rhs = []

        # TODO: make this more declarative

        for key, value in filters:
            name = mapper(key, type="document")

            if key == "begin_registratie":
                # begin_registratie is a LTE filter, so define it as such:
                column = mapper("begin_registratie", type="document")
                _lhs.append(f"{column} <= '%s'")
                _rhs.append(value.isoformat().replace("+00:00", "Z"))
                continue
            elif key == "_va_order":
                continue
            elif key == "informatieobjecttype":
                if isinstance(value, list) and len(value) == 0:
                    # In this case there are no authorised informatieobjecttypes
                    _lhs.append("drc:document__informatieobjecttype = '%s'")
                    _rhs.append("")
                    continue
                else:
                    # In this case there are multiple allowed informatieobjecttypes
                    lhs, rhs = self._build_authorisation_filter(name, value)
                    _lhs.append(lhs)
                    _rhs += rhs
                    continue
            elif key == "creatiedatum" and value == "":
                _lhs.append(f"{name} LIKE '%s'")
                _rhs.append("%-%-%")
                continue

            if name is None:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            _rhs.append(value)
            _lhs.append(f"{name} = '%s'")

        return _lhs, _rhs

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = None
        for key, value in filters:
            if key == "pk" and isinstance(value, CMISQuerySet):
                new_filters = value._cmis_query
                break

        return new_filters or filters

    def _needs_vertrowelijkaanduiding_filter(self, filters: List[Tuple]) -> bool:
        return "_va_order" in dict(filters)

    def _filter_by_va(self, filters: List[Tuple], documents: List) -> List:
        if len(documents) == 0:
            return documents

        # get the vertrowelijkaanduiding filter
        for filter_name, filter_value in filters:
            if filter_name == "_va_order":
                # In case there are multiple different vertrouwelijk aanduiding,
                # it chooses the lowest one
                all_vertrouwelijkaanduiding = []
                if isinstance(filter_value, list):
                    for order in filter_value:
                        for case in order.cases:
                            all_vertrouwelijkaanduiding.append(
                                case.result.identity[1][1]
                            )

                else:
                    for case in filter_value.cases:
                        all_vertrouwelijkaanduiding.append(case.result.identity[1][1])
                va_order = min(all_vertrouwelijkaanduiding)
                break

        filtered_docs = []
        for cmis_doc in documents:
            # Check that the vertrouwelijkaanduiding autorisation is as required
            django_doc = cmis_doc_to_django_model(cmis_doc)
            doc_va_order = get_doc_va_order(django_doc)
            if doc_va_order <= va_order:
                filtered_docs.append(cmis_doc)

        return filtered_docs

    def _build_authorisation_filter(
        self, key: str, value: List
    ) -> Tuple[str, List[str]]:
        """
        :param key: Alfresco name of the property to filter on
        :param value: List of the values that the key should take
        """
        lhs = "( "
        for _ in value:
            lhs += f"{key} = '%s' OR "
        # stripping the last OR
        lhs = lhs[:-3] + ")"

        return lhs, value


class CMISOioIterable(BaseIterable):

    table = "drc:oio"
    return_type = "Oio"

    def __iter__(self):
        queryset = self.queryset

        filters = self._check_for_pk_filter(queryset._cmis_query)
        unique_filters = self._combine_duplicate_filters(filters)

        lhs, rhs = self._normalize_filters(unique_filters)
        oios = queryset.cmis_client.query(self.return_type, lhs, rhs)
        # To avoid attempting prefetch of the canonical objects
        queryset._prefetch_done = True

        for oio in oios:
            yield cmis_oio_to_django(oio)

    def _normalize_filters(self, filters: List[Tuple]) -> Tuple[List[str], List[str]]:
        """
        Normalize the various flavours of ORM filters.

        Turn dict filters into something that looks like SQL 92 suitable for Alfresco
        CMIS query. Note that all filters are AND-ed together.

        Ideally, this would be an implementation of the as_sql for a custom database
        backend, returning lhs and rhs parts.
        """
        _lhs = []
        _rhs = []

        for key, value in filters:
            name = mapper(key, type="oio")

            if name is None:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            lhs_filter, rhs_filter = build_filter(name, value)

            _rhs += rhs_filter
            _lhs += lhs_filter

        return _lhs, _rhs

    def _combine_duplicate_filters(self, filters: List[Tuple]) -> List[Tuple]:
        unique_filters = {}
        for key, value in filters:
            if unique_filters.get(key) is None:
                unique_filters[key] = value
            else:
                unique_filters[key] = modify_value_in_dictionary(
                    unique_filters[key], value
                )

        formatted_unique_filters = []
        for key, value in unique_filters.items():
            formatted_unique_filters.append((key, value))

        return formatted_unique_filters

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = []
        for key, value in filters:
            if key == "pk" and isinstance(value, ObjectInformatieObjectCMISQuerySet):
                new_filters += value._cmis_query
            else:
                new_filters.append((key, value))

        return new_filters


class CMISGebruiksrechtenIterable(BaseIterable):
    table = "drc:gebruiksrechten"
    return_type = "Gebruiksrechten"

    def __iter__(self):
        queryset = self.queryset

        filters = self._check_for_pk_filter(queryset._cmis_query)
        unique_filters = self._combine_duplicate_filters(filters)

        lhs, rhs = self._normalize_filters(unique_filters)
        gebruiksrechten_cmis = queryset.cmis_client.query(self.return_type, lhs, rhs)
        # To avoid attempting prefetch of the canonical objects
        queryset._prefetch_done = True

        for gebruiksrechten_doc in gebruiksrechten_cmis:
            yield cmis_gebruiksrechten_to_django(gebruiksrechten_doc)

    def _normalize_filters(self, filters: List[Tuple]) -> Tuple[List[str], List[str]]:
        """
        Normalize the various flavours of ORM filters.

        Turn dict filters into something that looks like SQL 92 suitable for Alfresco
        CMIS query. Note that all filters are AND-ed together.

        Ideally, this would be an implementation of the as_sql for a custom database
        backend, returning lhs and rhs parts.
        """
        _lhs = []
        _rhs = []

        for key, value in filters:
            name = mapper(key, type="gebruiksrechten")

            if name is None:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            lhs_filter, rhs_filter = build_filter(name, value)

            _rhs += rhs_filter
            _lhs += lhs_filter

        return _lhs, _rhs

    def _combine_duplicate_filters(self, filters: List[Tuple]) -> List[Tuple]:
        unique_filters = {}
        for key, value in filters:
            if unique_filters.get(key) is None:
                unique_filters[key] = value
            else:
                unique_filters[key] = modify_value_in_dictionary(
                    unique_filters[key], value
                )

        formatted_unique_filters = []
        for key, value in unique_filters.items():
            formatted_unique_filters.append((key, value))

        return formatted_unique_filters

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = []
        for key, value in filters:
            if key == "pk" and isinstance(value, GebruiksrechtenQuerySet):
                new_filters += value._cmis_query
            else:
                new_filters.append((key, value))

        return new_filters


# --------------- Querysets --------------------------


class CMISQuerySet(InformatieobjectQuerySet, CMISClientMixin):
    """
    Find more information about the drc-cmis adapter on github here.
    https://github.com/GemeenteUtrecht/gemma-drc-cmis
    """

    documents = []
    has_been_filtered = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISDocumentIterable

        self._cmis_query = []

    def _clone(self):
        clone = super()._clone()
        clone._cmis_query = copy.copy(self._cmis_query)
        return clone

    def iterator(self):
        # loop though the results to return them when requested.
        # Not tested with a filter attached to the all call.
        for document in self.documents:
            yield document

    def exists(self):
        if self._result_cache is None:
            return bool(len(self))
        return bool(self._result_cache)

    def count(self):
        if self._result_cache is not None:
            return len(self._result_cache)

        return len(self)

    def union(self, *args, **kwargs):
        unified_queryset = super().union(*args, **kwargs)

        unified_query = {}
        for key, value in self._cmis_query:
            unified_query[key] = value

        # Adding the cmis queries of the other qs
        for qs in args:
            if isinstance(qs, CMISQuerySet):
                for key, value in qs._cmis_query:
                    if unified_query.get(key) is not None:
                        if isinstance(unified_query.get(key), list) and isinstance(
                            value, list
                        ):
                            unified_query[key] += value
                        elif isinstance(unified_query.get(key), list):
                            unified_query[key].append(value)
                        else:
                            unified_query[key] = [unified_query.get(key), value]
                    else:
                        unified_query[key] = value

        unified_queryset._cmis_query = [tuple(x) for x in unified_query.items()]

        return unified_queryset

    def create(self, **kwargs):
        # we don't use this structure
        kwargs.pop("canonical")

        # The url needs to be added manually because the drc_cmis uses the 'omshrijving' as the value
        # of the informatie object type
        kwargs["informatieobjecttype"] = get_object_url(
            kwargs.get("informatieobjecttype"), request=kwargs.get("_request"),
        )

        # The begin_registratie field needs to be populated (could maybe be moved in cmis library?)
        kwargs["begin_registratie"] = timezone.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        for key, value in kwargs.items():
            if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                kwargs[key] = value.strftime("%Y-%m-%dT%H:%M:%S.%f")

        content = kwargs.pop("inhoud", None)

        try:
            # Needed because the API calls the create function for an update request
            new_cmis_document = self.cmis_client.update_document(
                drc_uuid=kwargs.get("uuid"),
                lock=kwargs.get("lock"),
                data=kwargs,
                content=content,
            )
        except exceptions.DocumentDoesNotExistError:
            kwargs.setdefault("versie", "1")
            new_cmis_document = self.cmis_client.create_document(
                identification=kwargs.get("identificatie"),
                data=kwargs,
                content=content,
            )

        django_document = cmis_doc_to_django_model(new_cmis_document)

        # If no identificatie field is present, use the same as the document uuid (issue #762)
        if not django_document.identificatie:
            django_document.identificatie = django_document.uuid
            model_data = model_to_dict(django_document)
            self.filter(uuid=django_document.uuid).update(**model_data)

        return django_document

    def filter(self, *args, **kwargs):

        clone = super().filter(*args, **kwargs)

        filters = self._construct_filters(**kwargs)

        # keep track of all the filters when chaining
        clone._cmis_query += [tuple(x) for x in filters.items()]

        return clone

    def _construct_filters(self, **kwargs) -> dict:
        filters = {}

        # Limit filter to just exact lookup for now (until implemented in drc_cmis)
        for key, value in kwargs.items():
            key_bits = key.split("__")
            if len(key_bits) > 1 and key_bits[1] not in [
                "exact",
                "in",
                "lte",
                "regex",
                "isnull",
            ]:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")
            if "informatieobjecttype" in key:
                if isinstance(value, list):
                    filters["informatieobjecttype"] = [
                        get_object_url(item) for item in value
                    ]
                else:
                    filters["informatieobjecttype"] = get_object_url(value)
            elif key == "identificatie__regex":
                if "%" in value:
                    filters[key_bits[0]] = value
                else:
                    raise NotImplementedError(
                        f"Filter on '{key}' is not implemented yet"
                    )
            elif key == "creatiedatum__isnull":
                filters["creatiedatum"] = ""
            else:
                filters[key_bits[0]] = value

        return filters

    def update(self, **kwargs):
        docs_to_update = super().iterator()

        updated = 0
        seen = set()

        if kwargs.get("inhoud") == "":
            kwargs["inhoud"] = None

        for django_doc in docs_to_update:
            # skip over duplicate canonicals!
            if django_doc.uuid in seen:
                continue
            seen.add(django_doc.uuid)
            updated += 1

            canonical_obj = django_doc.canonical
            canonical_obj.lock_document(doc_uuid=django_doc.uuid)
            self.cmis_client.update_document(
                drc_uuid=django_doc.uuid,
                lock=canonical_obj.lock,
                data=kwargs,
                content=kwargs.get("inhoud"),
            )
            canonical_obj.unlock_document(
                doc_uuid=django_doc.uuid, lock=canonical_obj.lock
            )

        # Should return the number of rows that have been modified
        return updated

    # FIXME This is a temporary fix to make date_hierarchy work for the admin,
    #  so that EIOs can be viewed
    def dates(self, field_name, kind, order="ASC"):
        filter = {f"{field_name}__isnull": False}
        filtered_qs = self.filter(**filter)
        for item in filtered_qs:
            date = getattr(item, field_name)
            yield date


class GebruiksrechtenQuerySet(InformatieobjectRelatedQuerySet, CMISClientMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISGebruiksrechtenIterable

        self._cmis_query = []

    def _clone(self):
        clone = super()._clone()
        clone._cmis_query = copy.copy(self._cmis_query)
        return clone

    def create(self, **kwargs):
        from ..models import EnkelvoudigInformatieObject

        for key, value in kwargs.items():
            if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                kwargs[key] = value.strftime("%Y-%m-%dT%H:%M:%S.%f")

        cmis_gebruiksrechten = self.cmis_client.create_content_object(
            data=kwargs, object_type="gebruiksrechten"
        )

        # Get EnkelvoudigInformatieObject uuid from URL
        uuid = kwargs.get("informatieobject").split("/")[-1]
        modified_data = {"indicatie_gebruiksrecht": True}
        EnkelvoudigInformatieObject.objects.filter(uuid=uuid).update(**modified_data)

        django_gebruiksrechten = cmis_gebruiksrechten_to_django(cmis_gebruiksrechten)

        return django_gebruiksrechten

    def filter(self, *args, **kwargs):

        filters = self.process_filters(kwargs)

        self._cmis_query += [tuple(x) for x in filters.items()]

        return self

    def exists(self):
        if self._result_cache is None:
            return bool(len(self))
        return bool(self._result_cache)

    def none(self):
        """Adds a query to the _cmis_query that will match nothing"""
        clone = self._chain()
        clone._cmis_query = [("uuid", "")]
        return clone

    def process_filters(self, data):

        converted_data = {}

        for key, value in data.items():
            split_key = key.split("__")
            split_key[0] = split_key[0].strip("_")
            if len(split_key) > 1 and split_key[1] not in ["exact", "in"]:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            # If the value is a queryset, extract the objects
            if split_key[0] == "informatieobject" and isinstance(value, CMISQuerySet):
                list_value = []
                for item in value:
                    list_value.append(make_absolute_uri(reverse(item)))
                value = list_value

            converted_data[split_key[0]] = value

        return converted_data


class ObjectInformatieObjectCMISQuerySet(
    ObjectInformatieObjectQuerySet, CMISClientMixin
):

    has_been_filtered = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISOioIterable

        self._cmis_query = []

    def _clone(self):
        clone = super()._clone()
        clone._cmis_query = copy.copy(self._cmis_query)
        return clone

    def count(self):
        if self._result_cache is not None:
            return len(self._result_cache)

        return len(self)

    def process_filters(self, data):

        converted_data = {}

        if data.get("object_type"):
            object_type = data.pop("object_type")
            if data.get(object_type):
                relation_object = data.pop(object_type)
            else:
                relation_object = data.pop("object")
            relation_url = get_object_url(relation_object)
            if relation_url is None:
                relation_url = make_absolute_uri(reverse(relation_object))
            converted_data["object_type"] = object_type
            converted_data[f"{object_type}"] = relation_url

        for key, value in data.items():
            split_key = key.split("__")
            split_key[0] = split_key[0].strip("_")
            if len(split_key) > 1 and split_key[1] not in ["exact", "in"]:
                raise NotImplementedError(
                    "Fields lookups other than exact are not implemented yet."
                )

            # If the value is a queryset, extract the objects
            if split_key[0] == "informatieobject" and isinstance(value, CMISQuerySet):
                list_value = []
                for item in value:
                    list_value.append(make_absolute_uri(reverse(item)))
                value = list_value

            if split_key[0] in ["besluit", "zaak"]:
                converted_data[split_key[0]] = make_absolute_uri(reverse(value))
            elif split_key[0] in ["besluit_url", "zaak_url"]:
                converted_data[split_key[0].split("_")[0]] = value
            else:
                converted_data[split_key[0]] = value

        return converted_data

    def create(self, **kwargs):
        data = self.process_filters(kwargs)

        if data.get("zaak") is not None and data.get("besluit") is not None:
            raise IntegrityError(
                "ObjectInformatie object cannot have both Zaak and Besluit relation"
            )
        elif data.get("zaak") is None and data.get("besluit") is None:
            raise IntegrityError(
                "ObjectInformatie object needs to have either a Zaak or Besluit relation"
            )

        cmis_oio = self.cmis_client.create_oio(data=data)
        django_oio = cmis_oio_to_django(cmis_oio)
        return django_oio

    def create_from(self, relation):
        object_type = self.RELATIONS[type(relation)]
        relation_object = getattr(relation, object_type)
        data = {
            "informatieobject": relation._informatieobject_url,
            "object_type": f"{object_type}",
            f"{object_type}": make_absolute_uri(reverse(relation_object)),
        }
        return self.create(**data)

    def delete_for(self, relation):
        object_type = self.RELATIONS[type(relation)]
        relation_object = getattr(relation, object_type)
        filters = {
            "informatieobject": relation._informatieobject_url,
            "object_type": f"{object_type}",
            "object": relation_object,
        }
        obj = self.get(**filters)
        return obj.delete()

    def filter(self, *args, **kwargs):
        filters = self.process_filters(kwargs)

        if filters.get("object_type"):
            filters.pop("object_type")

        # keep track of all the filters when chaining
        self._cmis_query += [tuple(x) for x in filters.items()]

        return self

    def exists(self):
        if self._result_cache is None:
            return bool(len(self))
        return bool(self._result_cache)


# ---------------- Utility Functions --------------------


def convert_timestamp_to_django_datetime(json_date):
    """
    Takes an int such as 1467717221000 as input and returns 2016-07-05 as output.
    """
    if json_date is not None:
        timestamp = int(str(json_date)[:10])
        django_datetime = timezone.make_aware(
            datetime.datetime.fromtimestamp(timestamp)
        )
        return django_datetime


def format_fields(obj, obj_fields):
    """
    Ensuring the charfields are not null and dates are in the correct format
    """
    for field in obj_fields:
        _value = getattr(obj, field.name, None)
        if isinstance(field, fields.CharField) or isinstance(field, fields.TextField):
            if _value is None:
                setattr(obj, field.name, "")
        elif isinstance(field, fields.DateTimeField):
            if isinstance(_value, int):
                setattr(obj, field.name, convert_timestamp_to_django_datetime(_value))
            elif isinstance(_value, str):
                setattr(
                    obj,
                    field.name,
                    datetime.datetime.strptime(_value, "%Y-%m-%dT%H:%M:%S.%f%z"),
                )
        elif isinstance(field, fields.DateField):
            if isinstance(_value, int):
                converted_datetime = convert_timestamp_to_django_datetime(_value)
                setattr(obj, field.name, converted_datetime.date())
            elif isinstance(_value, str):
                converted_datetime = datetime.datetime.strptime(
                    _value, "%Y-%m-%dT%H:%M:%S.%f%z"
                )
                setattr(obj, field.name, converted_datetime.date())
            elif isinstance(_value, datetime.datetime):
                setattr(obj, field.name, _value.date())
    return obj


def cmis_doc_to_django_model(
    cmis_doc: Cmisdoc,
    skip_pwc: bool = False,
    version: Optional[int] = None,
    begin_registratie: Optional[datetime.datetime] = None,
):
    from ..models import (
        EnkelvoudigInformatieObject,
        EnkelvoudigInformatieObjectCanonical,
    )

    # get the pwc and continue to operate on the PWC
    if not skip_pwc and cmis_doc.isVersionSeriesCheckedOut:
        pwc = cmis_doc.get_latest_version()
        # check if the PWC does still match the detail filters, if provided
        version_ok = version and version == pwc.versie
        begin_registratie_ok = (
            begin_registratie and pwc.begin_registratie <= begin_registratie
        )
        if (not version or version_ok) and (
            not begin_registratie or begin_registratie_ok
        ):
            cmis_doc = pwc

    # The if the document is locked, the lock_id is stored in versionSeriesCheckedOutId
    canonical = EnkelvoudigInformatieObjectCanonical()
    canonical.lock = cmis_doc.lock or ""

    # Ensuring the charfields are not null and dates are in the correct format
    cmis_doc = format_fields(cmis_doc, EnkelvoudigInformatieObject._meta.get_fields())

    # Setting up a local file with the content of the cmis document
    # Replacing the alfresco version (decimal) with the custom version label
    uuid_with_version = f"{cmis_doc.uuid};{cmis_doc.versie}"
    content_file = CMISStorageFile(uuid_version=uuid_with_version)

    document = EnkelvoudigInformatieObject(
        uuid=uuid.UUID(cmis_doc.uuid),
        auteur=cmis_doc.auteur,
        begin_registratie=cmis_doc.begin_registratie,
        beschrijving=cmis_doc.beschrijving,
        bestandsnaam=cmis_doc.bestandsnaam,
        bronorganisatie=cmis_doc.bronorganisatie,
        creatiedatum=cmis_doc.creatiedatum,
        formaat=cmis_doc.formaat,
        canonical=canonical,
        identificatie=cmis_doc.identificatie,
        indicatie_gebruiksrecht=cmis_doc.indicatie_gebruiksrecht,
        informatieobjecttype=cmis_doc.informatieobjecttype,
        inhoud=content_file,
        integriteit_algoritme=cmis_doc.integriteit_algoritme,
        integriteit_datum=cmis_doc.integriteit_datum,
        integriteit_waarde=cmis_doc.integriteit_waarde,
        link=cmis_doc.link,
        ontvangstdatum=cmis_doc.ontvangstdatum,
        status=cmis_doc.status,
        taal=cmis_doc.taal,
        titel=cmis_doc.titel,
        versie=cmis_doc.versie,
        vertrouwelijkheidaanduiding=cmis_doc.vertrouwelijkheidaanduiding,
        verzenddatum=cmis_doc.verzenddatum,
    )

    return document


def cmis_gebruiksrechten_to_django(cmis_gebruiksrechten):

    from ..models import EnkelvoudigInformatieObjectCanonical, Gebruiksrechten

    canonical = EnkelvoudigInformatieObjectCanonical()

    cmis_gebruiksrechten = format_fields(
        cmis_gebruiksrechten, Gebruiksrechten._meta.get_fields()
    )

    django_gebruiksrechten = Gebruiksrechten(
        uuid=uuid.UUID(cmis_gebruiksrechten.uuid),
        informatieobject=canonical,
        omschrijving_voorwaarden=cmis_gebruiksrechten.omschrijving_voorwaarden,
        startdatum=cmis_gebruiksrechten.startdatum,
        einddatum=cmis_gebruiksrechten.einddatum,
    )

    return django_gebruiksrechten


def cmis_oio_to_django(cmis_oio):

    from ..models import EnkelvoudigInformatieObjectCanonical, ObjectInformatieObject

    canonical = EnkelvoudigInformatieObjectCanonical()

    django_oio = ObjectInformatieObject(
        uuid=uuid.UUID(cmis_oio.uuid),
        informatieobject=canonical,
        zaak=cmis_oio.zaak,
        besluit=cmis_oio.besluit,
        object_type=cmis_oio.object_type,
    )

    return django_oio


def get_object_url(
    informatie_obj_type: InformatieObjectType, request: Optional[Request] = None
):
    """
    Retrieves the url for the informatieobjecttypes and virtual informatieobjecttype (used for external
    informatieobjecttype).
    """
    # Case in which the informatie_object_type is already a url
    if isinstance(informatie_obj_type, str):
        return informatie_obj_type
    elif isinstance(informatie_obj_type, ProxyMixin):
        return informatie_obj_type._initial_data["url"]
    elif isinstance(informatie_obj_type, InformatieObjectType):
        path = informatie_obj_type.get_absolute_api_url()
        return make_absolute_uri(path, request=request)


def get_doc_va_order(django_doc):
    choice_item = VertrouwelijkheidsAanduiding.get_choice(
        django_doc.vertrouwelijkheidaanduiding
    )
    return choice_item.order


def build_filter(filter_name, filter_value):
    rhs = []
    lhs = []

    if isinstance(filter_value, list):
        if len(filter_value) == 0:
            lhs.append(f"{filter_name} = '%s'")
            rhs.append("")
        else:
            lhs_string = "( "
            for item in filter_value:
                lhs_string += f"{filter_name} = '%s' OR "
                rhs.append(item)
            # stripping the last OR
            lhs_string = lhs_string[:-3] + ")"
            lhs.append(lhs_string)
    else:
        lhs.append(f"{filter_name} = '%s'")
        rhs.append(filter_value)

    return lhs, rhs


def modify_value_in_dictionary(existing_value, new_value):
    """
    Checks if the key in the dictionary is already a list and then adds the new value accordingly.
    """
    if isinstance(existing_value, list) and isinstance(new_value, list):
        existing_value += new_value
    elif isinstance(existing_value, list):
        existing_value.append(new_value)
    else:
        existing_value = [existing_value, new_value]

    return existing_value
