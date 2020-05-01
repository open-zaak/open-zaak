import copy
import datetime
import re
from decimal import Decimal, InvalidOperation
from drc_cmis.client import CMISDRCClient, exceptions
from drc_cmis.backend import CMISDRCStorageBackend
import logging
from vng_api_common.tests import reverse
from drc_cmis.cmis.drc_document import Document, ObjectInformatieObject, Gebruiksrechten
from drc_cmis.client.mapper import mapper
from drc_cmis.client.convert import make_absolute_uri
from typing import List, Optional, Tuple
from rest_framework.request import Request
from vng_api_common.constants import VertrouwelijkheidsAanduiding
# from vng_api_common.utils import generate_unique_identification

from django.conf import settings
from django.db import models
from django.db.models import fields
from django.forms.models import model_to_dict
from django.utils import timezone
from django.db.models.query import BaseIterable
from django_loose_fk.virtual_models import ProxyMixin

from ..catalogi.models.informatieobjecttype import InformatieObjectType
from .query import (
    InformatieobjectQuerySet,
    InformatieobjectRelatedQuerySet,
    ObjectInformatieObjectQuerySet,
)
from .utils import CMISStorageFile

logger = logging.getLogger(__name__)

# ---------------------- Iterable classes -----------

RHS_FILTER_MAP = {
    "_informatieobjecttype__in": lambda val: [get_object_url(item) for item in val],
    "identificatie": lambda val: f"drc:document__identificatie = '{val}'",
}

LHS_FILTER_MAP = {
    "_informatieobjecttype__in": "informatieobjecttype__in",
}

#TODO Refactor so that all these iterables inherit from a class that implements the shared functionality
class CMISDocumentIterable(BaseIterable):

    table = "drc:document"
    return_type = Document

    def __iter__(self):
        queryset = self.queryset

        filters = self._check_for_pk_filter(queryset._cmis_query)

        lhs, rhs = self._normalize_filters(filters)
        documents = queryset.cmis_client.query(self.return_type, lhs, rhs)

        if self._needs_older_version(filters):
            documents = self._retrive_older_version(filters, documents)
        elif self._needs_registratie_filter(filters):
            documents = self._filter_by_registratie(filters, documents)
        elif self._needs_vertrowelijkaanduiding_filter(filters):
            documents = self._filter_by_va(filters, documents)

        for document in documents:
            yield cmis_doc_to_django_model(document)

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

            if key == 'uuid':
                name = 'cmis:objectId'
                value = f'workspace://SpacesStore/{value};1.0'
            elif key == 'versie':
                # The older versions can be accessed once the latest document is available
                continue
            elif key == 'begin_registratie':
                # In order to retrieve all the versions from before a certain date, the latest document is needed
                continue
            elif key == '_va_order':
                continue
            elif key == 'informatieobjecttype':
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
            elif key == 'identificatie' and '%' in value:
                _lhs.append(f"{name} LIKE '%s'")
                _rhs.append(f"{value}")
                continue

            if name is None:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            _rhs.append(value)
            _lhs.append(f"{name} = '%s'")

        return _lhs, _rhs

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = None
        for key, value in filters:
            if key == 'pk' and isinstance(value, CMISQuerySet):
                new_filters = value._cmis_query
                break

        if new_filters:
            return new_filters
        else:
            return filters

    def _needs_older_version(self, filters: List[Tuple]) -> bool:
        for key, value in filters:
            if key == 'versie':
                return True
        return False

    def _needs_registratie_filter(self, filters: List[Tuple]) -> bool:
        for key, value in filters:
            if key == 'begin_registratie':
                return True
        return False

    def _needs_vertrowelijkaanduiding_filter(self, filters: List[Tuple]) -> bool:
        for key, value in filters:
            if key == '_va_order':
                return True
        return False

    #FIXME
    # This wont work if various versions of different documents have to be retrieved
    def _retrive_older_version(self, filters: List[Tuple], documents: List) -> List:
        """
        Older versions of documents cannot be retrieved directly through the uuid. More info:
        https://hub.alfresco.com/t5/alfresco-content-services-forum/how-to-generate-document-location-url-for-previous-verions-using/td-p/279115
        """
        older_versions_documents = []

        for key, value in filters:
            if key == 'versie':
                version_needed = str(value)

        for cmis_doc in documents:
            all_versions = cmis_doc.get_all_versions()
            for version_number, cmis_document in all_versions.items():
                if version_number == version_needed:
                    older_versions_documents.append(cmis_document)
        return older_versions_documents

    def _filter_by_registratie(self, filters: List[Tuple], documents: List) -> List:

        before_date_documents = []

        for key, value in filters:
            if key == 'begin_registratie':
                requested_date = value

        for cmis_doc in documents:
            all_versions = cmis_doc.get_all_versions()
            for versie, cmis_document in all_versions.items():
                if (
                    convert_timestamp_to_django_datetime(
                        cmis_document.begin_registratie
                    )
                    <= requested_date
                ):
                    before_date_documents.append(cmis_document)
                    break
        return before_date_documents

    def _filter_by_va(self, filters: List[Tuple], documents: List) -> List:
        if len(documents) == 0:
            return documents

        # get the vertrowelijkaanduiding filter
        for filter_name, filter_value in filters:
            if filter_name == '_va_order':
                # In case there are multiple different vertrouwelijk aanduiding,
                # it chooses the lowest one
                all_vertrowelijkaanduiding = []
                if isinstance(filter_value, list):
                    for order in filter_value:
                        for case in order.cases:
                            all_vertrowelijkaanduiding.append(case.result.identity[1][1])

                else:
                    for case in filter_value.cases:
                        all_vertrowelijkaanduiding.append(case.result.identity[1][1])
                va_order = min(all_vertrowelijkaanduiding)
                break

        filtered_docs = []
        for cmis_doc in documents:
            # Check that the vertrouwelijkaanduiding autorisation is as required
            django_doc = cmis_doc_to_django_model(cmis_doc)
            doc_va_order = get_doc_va_order(django_doc)
            if doc_va_order <= va_order:
                filtered_docs.append(cmis_doc)

        return filtered_docs

    def _build_authorisation_filter(self, key: str, value: List) -> Tuple[str, List[str]]:
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
    return_type = ObjectInformatieObject

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
            name = mapper(key, type="objectinformatieobject")

            if key == 'uuid':
                name = 'cmis:objectId'
                value = f'workspace://SpacesStore/{value};1.0'

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
                unique_filters[key] = modify_value_in_dictionary(unique_filters[key], value)

        formatted_unique_filters = []
        for key, value in unique_filters.items():
            formatted_unique_filters.append((key, value))

        return formatted_unique_filters

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = []
        for key, value in filters:
            if key == 'pk' and isinstance(value, ObjectInformatieObjectCMISQuerySet):
                new_filters += value._cmis_query
            else:
                new_filters.append((key, value))

        return new_filters


class CMISGebruiksrechtenIterable(BaseIterable):
    table = "drc:gebruiksrechten"
    return_type = Gebruiksrechten

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

            if key == 'uuid':
                name = 'cmis:objectId'
                value = f'workspace://SpacesStore/{value};1.0'

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
                unique_filters[key] = modify_value_in_dictionary(unique_filters[key], value)

        formatted_unique_filters = []
        for key, value in unique_filters.items():
            formatted_unique_filters.append((key, value))

        return formatted_unique_filters

    def _check_for_pk_filter(self, filters: List[Tuple]) -> List[Tuple]:
        new_filters = []
        for key, value in filters:
            if key == 'pk' and isinstance(value, GebruiksrechtenQuerySet):
                new_filters += value._cmis_query
            else:
                new_filters.append((key, value))

        return new_filters


# --------------- Querysets --------------------------


class DjangoQuerySet(InformatieobjectQuerySet):
    pass


class CMISQuerySet(InformatieobjectQuerySet):
    """
    Find more information about the drc-cmis adapter on github here.
    https://github.com/GemeenteUtrecht/gemma-drc-cmis
    """

    _client = None
    documents = []
    has_been_filtered = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISDocumentIterable

        self._cmis_query = []

    @property
    def cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

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
                        if isinstance(unified_query.get(key), list) and isinstance(value, list):
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
        # The url needs to be added manually because the drc_cmis uses the 'omshrijving' as the value
        # of the informatie object type
        kwargs["informatieobjecttype"] = get_object_url(
            kwargs.get("informatieobjecttype"), request=kwargs.get("_request"),
        )

        # The begin_registratie field needs to be populated (could maybe be moved in cmis library?)
        kwargs["begin_registratie"] = timezone.now()

        try:
            # Needed because the API calls the create function for an update request
            new_cmis_document = self.cmis_client.update_cmis_document(
                uuid=kwargs.get("uuid"),
                lock=kwargs.get("lock"),
                data=kwargs,
                content=kwargs.get("inhoud"),
            )
        except exceptions.DocumentDoesNotExistError:
            new_cmis_document = self.cmis_client.create_document(
                identification=kwargs.get("identificatie"),
                data=kwargs,
                content=kwargs.get("inhoud"),
            )

        django_document = cmis_doc_to_django_model(new_cmis_document)

        # If no identificatie field is present, it generates a unique, human readable one
        if not django_document.identificatie:
            #FIXME when aggregation operations will work in alfresco, should use
            # vng_api_common.utils.generate_unique_identification rather than the one defined below
            django_document.identificatie = generate_unique_identification(django_document, "creatiedatum")
            model_data = model_to_dict(django_document)
            self.filter(uuid=django_document.uuid).update(**model_data)

        return django_document

    def filter(self, *args, **kwargs):
        filters = {}

        # Limit filter to just exact lookup for now (until implemented in drc_cmis)
        for key, value in kwargs.items():
            key_bits = key.split("__")
            if len(key_bits) > 1 and key_bits[1] not in ["exact", "in", "lte", "regex"]:
                raise NotImplementedError(
                    f"Fields lookups other than exact are not implemented yet (searched key: {key})"
                )
            if 'informatieobjecttype' in key:
                if isinstance(value, list):
                    filters['informatieobjecttype'] = [get_object_url(item) for item in value]
                else:
                    filters['informatieobjecttype'] = get_object_url(value)
            elif key == 'identificatie__regex':
                if "%" in value:
                    filters[key_bits[0]] = value
                else:
                    raise NotImplementedError(
                        f"This regex field lookup has not been implemented yet (searched key: {key})"
                    )
            else:
                filters[key_bits[0]] = value


        # keep track of all the filters when chaining
        self._cmis_query += [tuple(x) for x in filters.items()]

        return super().filter(*args, **kwargs)

        # # TODO

        # self._result_cache = []

        # try:
        #     if filters.get("identificatie") is not None:
        #         client = self.cmis_client
        #         cmis_doc = client.get_cmis_document(
        #             identification=filters.get("identificatie"),
        #             via_identification=True,
        #             filters=None,
        #         )
        #         self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
        #     elif filters.get("versie") is not None and filters.get("uuid") is not None:
        #         cmis_doc = self.cmis_client.get_cmis_document(
        #             identification=filters.get("uuid"),
        #             via_identification=False,
        #             filters=None,
        #         )
        #         all_versions = cmis_doc.get_all_versions()
        #         for version_number, cmis_document in all_versions.items():
        #             if version_number == str(filters["versie"]):
        #                 self._result_cache.append(
        #                     cmis_doc_to_django_model(cmis_document)
        #                 )
        #     elif (
        #         filters.get("registratie_op") is not None
        #         and filters.get("uuid") is not None
        #     ):
        #         cmis_doc = self.cmis_client.get_cmis_document(
        #             identification=filters.get("uuid"),
        #             via_identification=False,
        #             filters=None,
        #         )
        #         all_versions = cmis_doc.get_all_versions()
        #         for versie, cmis_document in all_versions.items():
        #             if (
        #                 convert_timestamp_to_django_datetime(
        #                     cmis_document.begin_registratie
        #                 )
        #                 <= filters["registratie_op"]
        #             ):
        #                 self._result_cache.append(
        #                     cmis_doc_to_django_model(cmis_document)
        #                 )
        #                 break
        #     elif filters.get("uuid") is not None:
        #         cmis_doc = self.cmis_client.get_cmis_document(
        #             identification=filters.get("uuid"),
        #             via_identification=False,
        #             filters=None,
        #         )
        #         self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
        #     else:
        #         # Filter the alfresco database
        #         cmis_documents = self.cmis_client.get_cmis_documents(
        #             filters=filters
        #         )
        #         for cmis_doc in cmis_documents["results"]:
        #             self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
        # except exceptions.DocumentDoesNotExistError:
        #     pass

        # self.documents = self._result_cache.copy()
        # self.has_been_filtered = True

        # return self

    # def get(self, *args, **kwargs):
    #
    #     if self.has_been_filtered:
    #         num = len(self._result_cache)
    #         if num == 1:
    #             return self._result_cache[0]
    #         if not num:
    #             raise self.model.DoesNotExist(
    #                 "%s matching query does not exist." % self.model._meta.object_name
    #             )
    #         raise self.model.MultipleObjectsReturned(
    #             "get() returned more than one %s -- it returned %s!"
    #             % (self.model._meta.object_name, num)
    #         )
    #     else:
    #         return super().get(*args, **kwargs)

    def delete(self):

        number_alfresco_updates = 0
        for django_doc in self._result_cache:
            try:
                if settings.CMIS_DELETE_IS_OBLITERATE:
                    # Actually removing the files from Alfresco
                    self.cmis_client.obliterate_document(django_doc.uuid)
                else:
                    # Updating all the documents from Alfresco to have 'verwijderd=True'
                    self.cmis_client.delete_cmis_document(django_doc.uuid)
                number_alfresco_updates += 1
            except exceptions.DocumentConflictException:
                logger.log(
                    f"Document met identificatie {django_doc.identificatie} kan niet worden gemarkeerd als verwijderd"
                )

        return number_alfresco_updates, {"cmis_document": number_alfresco_updates}

    def update(self, **kwargs):
        cmis_storage = CMISDRCStorageBackend()

        docs_to_update = list(super().iterator())
        number_docs_to_update = len(docs_to_update)

        if kwargs.get("inhoud") == "":
            kwargs["inhoud"] = None

        for django_doc in docs_to_update:
            canonical_obj = django_doc.canonical
            canonical_obj.lock_document(doc_uuid=django_doc.uuid)
            cmis_storage.update_document(
                uuid=django_doc.uuid,
                lock=canonical_obj.lock,
                data=kwargs,
                content=kwargs.get("inhoud"),
            )
            canonical_obj.unlock_document(
                doc_uuid=django_doc.uuid, lock=canonical_obj.lock
            )

            # Should return the number of rows that have been modified
            return number_docs_to_update


class GebruiksrechtenQuerySet(InformatieobjectRelatedQuerySet):

    _client = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISGebruiksrechtenIterable

        self._cmis_query = []

    @property
    def cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

    def _clone(self):
        clone = super()._clone()
        clone._cmis_query = copy.copy(self._cmis_query)
        return clone

    def create(self, **kwargs):
        from .models import EnkelvoudigInformatieObject

        cmis_gebruiksrechten = self.cmis_client.create_cmis_gebruiksrechten(data=kwargs)

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
        clone._cmis_query = [('uuid', '')]
        return clone

    def process_filters(self, data):

        converted_data = {}

        for key, value in data.items():
            split_key = key.split("__")
            split_key[0] = split_key[0].strip("_")
            if len(split_key) > 1 and split_key[1] not in ["exact", "in"]:
                raise NotImplementedError(
                    "Fields lookups other than exact are not implemented yet."
                )

            # If the value is a queryset, extract the objects
            if split_key[0] == 'informatieobject' and isinstance(value, CMISQuerySet):
                list_value = []
                for item in value:
                    list_value.append(make_absolute_uri(reverse(item)))
                value = list_value

            converted_data[split_key[0]] = value

        return converted_data


class ObjectInformatieObjectCMISQuerySet(ObjectInformatieObjectQuerySet):

    _client = None
    has_been_filtered = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._iterable_class = CMISOioIterable

        self._cmis_query = []

    @property
    def cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

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

        if data.get('object_type'):
            object_type = data.pop('object_type')
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
            if split_key[0] == 'informatieobject' and isinstance(value, CMISQuerySet):
                list_value = []
                for item in value:
                    list_value.append(make_absolute_uri(reverse(item)))
                value = list_value

            if split_key[0] in ['besluit', 'zaak']:
                converted_data[split_key[0]] = make_absolute_uri(reverse(value))
            elif split_key[0] in ['besluit_url', 'zaak_url']:
                converted_data[split_key[0].split("_")[0]] = value
            else:
                converted_data[split_key[0]] = value

        return converted_data

    def create(self, **kwargs):
        data = self.process_filters(kwargs)
        cmis_oio = self.cmis_client.create_cmis_oio(data=data)
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
            f"object": relation_object,
        }
        obj = self.get(**filters)
        return obj.delete()

    def filter(self, *args, **kwargs):
        filters = self.process_filters(kwargs)

        if filters.get('object_type'):
            filters.pop('object_type')

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
        if isinstance(field, fields.CharField) or isinstance(field, fields.TextField):
            if getattr(obj, field.name) is None:
                setattr(obj, field.name, "")
        elif isinstance(field, fields.DateTimeField):
            date_value = getattr(obj, field.name)
            if isinstance(date_value, int):
                setattr(
                    obj, field.name, convert_timestamp_to_django_datetime(date_value)
                )
        elif isinstance(field, fields.DateField):
            date_value = getattr(obj, field.name)
            if isinstance(date_value, int):
                converted_datetime = convert_timestamp_to_django_datetime(date_value)
                setattr(obj, field.name, converted_datetime.date())

    return obj


def cmis_doc_to_django_model(cmis_doc):
    from .models import (
        EnkelvoudigInformatieObject,
        EnkelvoudigInformatieObjectCanonical,
    )

    # The if the document is locked, the lock_id is stored in versionSeriesCheckedOutId
    canonical = EnkelvoudigInformatieObjectCanonical()
    canonical.lock = cmis_doc.versionSeriesCheckedOutId or ""

    versie = cmis_doc.versie
    try:
        int_versie = int(Decimal(versie) * 100)
    except ValueError:
        int_versie = 0
    except InvalidOperation:
        int_versie = 0

    # Ensuring the charfields are not null and dates are in the correct format
    cmis_doc = format_fields(cmis_doc, EnkelvoudigInformatieObject._meta.get_fields())

    # Setting up a local file with the content of the cmis document
    uuid_with_version = cmis_doc.versionSeriesId + ";" + cmis_doc.versie
    content_file = CMISStorageFile(uuid_version=uuid_with_version,)

    document = EnkelvoudigInformatieObject(
        auteur=cmis_doc.auteur,
        begin_registratie=cmis_doc.begin_registratie,
        beschrijving=cmis_doc.beschrijving,
        bestandsnaam=cmis_doc.bestandsnaam,
        bronorganisatie=cmis_doc.bronorganisatie,
        creatiedatum=cmis_doc.creatiedatum,
        formaat=cmis_doc.formaat,
        # id=cmis_doc.versionSeriesId,
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
        uuid=cmis_doc.versionSeriesId,
        versie=int_versie,
        vertrouwelijkheidaanduiding=cmis_doc.vertrouwelijkheidaanduiding,
        verzenddatum=cmis_doc.verzenddatum,
    )

    return document


def cmis_gebruiksrechten_to_django(cmis_gebruiksrechten):

    from .models import EnkelvoudigInformatieObjectCanonical, Gebruiksrechten

    canonical = EnkelvoudigInformatieObjectCanonical()

    cmis_gebruiksrechten = format_fields(
        cmis_gebruiksrechten, Gebruiksrechten._meta.get_fields()
    )

    django_gebruiksrechten = Gebruiksrechten(
        uuid=cmis_gebruiksrechten.versionSeriesId,
        informatieobject=canonical,
        omschrijving_voorwaarden=cmis_gebruiksrechten.omschrijving_voorwaarden,
        startdatum=cmis_gebruiksrechten.startdatum,
        einddatum=cmis_gebruiksrechten.einddatum,
    )

    return django_gebruiksrechten


def cmis_oio_to_django(cmis_oio):

    from .models import EnkelvoudigInformatieObjectCanonical, ObjectInformatieObject

    canonical = EnkelvoudigInformatieObjectCanonical()

    django_oio = ObjectInformatieObject(
        uuid=cmis_oio.versionSeriesId,
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


def generate_unique_identification(instance: models.Model, date_field_name: str):
    model = type(instance)
    model_name = getattr(model, "IDENTIFICATIE_PREFIX", model._meta.model_name.upper())

    year = getattr(instance, date_field_name).year
    pattern = f"{model_name}-{year}-%"

    issued_ids_for_year = model._default_manager.filter(identificatie__regex=pattern)

    max_identificatie = 0
    if issued_ids_for_year.exists():
        for document in issued_ids_for_year:
            number = int(document.identificatie.split("-")[-1])
            max_identificatie = max(max_identificatie, number)

    padded_number = str(max_identificatie+1).zfill(10)
    return f"{model_name}-{year}-{padded_number}"
