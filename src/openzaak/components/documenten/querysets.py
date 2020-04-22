import copy
import datetime
from decimal import Decimal, InvalidOperation
from drc_cmis.client import CMISDRCClient, exceptions
from drc_cmis.backend import CMISDRCStorageBackend
import logging
from vng_api_common.tests import reverse
from drc_cmis.cmis.drc_document import Document, ObjectInformatieObject
from drc_cmis.client.mapper import mapper
from drc_cmis.client.convert import make_absolute_uri
from typing import List, Optional, Tuple
from rest_framework.request import Request

from django.conf import settings
from django.db.models import fields
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


class CMISDocumentIterable(BaseIterable):

    table = "drc:document"
    return_type = Document

    def __iter__(self):
        queryset = self.queryset

        lhs, rhs = self._normalize_filters(queryset._cmis_query)
        documents = queryset.cmis_client.query(self.return_type, lhs, rhs)

        if self._needs_older_version(queryset._cmis_query):
            documents = self._retrive_older_version(queryset._cmis_query, documents)
        elif self._needs_registratie_filter(queryset._cmis_query):
            documents = self._filter_by_registratie(queryset._cmis_query, documents)

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

            if name is None:
                raise NotImplementedError(f"Filter on '{key}' is not implemented yet")

            _rhs.append(value)
            _lhs.append(f"{name} = '%s'")

        return _lhs, _rhs

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


class CMISOioIterable(BaseIterable):

    table = "drc:oio"
    return_type = ObjectInformatieObject

    def __iter__(self):
        queryset = self.queryset

        lhs, rhs = self._normalize_filters(queryset._cmis_query)
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

            _rhs.append(value)
            _lhs.append(f"{name} = '%s'")

        return _lhs, _rhs

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

    def count(self):
        if self._result_cache is not None:
            return len(self._result_cache)

        return len(self)

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

        # TODO needed to fix test src/openzaak/components/documenten/tests/models/test_human_readable_identification.py
        # but first filters on regex need to be implemented in alfresco
        # if not django_document.identificatie:
        #     django_document.identificatie = generate_unique_identification(django_document, "creatiedatum")
        #     model_data = model_to_dict(django_document)
        #     self.filter(uuid=django_document.uuid).update(**model_data)
        return django_document

    def filter(self, *args, **kwargs):
        filters = {}

        # Limit filter to just exact lookup for now (until implemented in drc_cmis)
        for key, value in kwargs.items():
            key_bits = key.split("__")
            if len(key_bits) > 1 and key_bits[1] != "exact":
                raise NotImplementedError(
                    "Fields lookups other than exact are not implemented yet."
                )
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
    has_been_filtered = False

    def __len__(self):
        # Overwritten to prevent prefetching of related objects
        return len(self._result_cache)

    @property
    def cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

    def _chain(self, **kwargs):
        obj = super()._chain(**kwargs)
        # In the super, when _clone() is performed on the queryset,
        # an SQL query is run to retrieve the objects, but with
        # alfresco it doesn't work, so the cache is re-added manually
        obj._result_cache = self._result_cache
        return obj

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

        self._result_cache = []

        cmis_gebruiksrechten = self.cmis_client.get_cmis_gebruiksrechten(kwargs)

        for a_cmis_gebruiksrechten in cmis_gebruiksrechten["results"]:
            self._result_cache.append(
                cmis_gebruiksrechten_to_django(a_cmis_gebruiksrechten)
            )

        self.has_been_filtered = True

        return self


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

    def convert_django_names_to_alfresco(self, data):

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
            if len(split_key) > 1 and split_key[1] != "exact":
                raise NotImplementedError(
                    "Fields lookups other than exact are not implemented yet."
                )

            if split_key[0] in ['besluit', 'zaak']:
                converted_data[split_key[0]] = make_absolute_uri(reverse(value))
            elif split_key[0] in ['besluit_url', 'zaak_url']:
                converted_data[split_key[0].split("_")[0]] = value
            else:
                converted_data[split_key[0]] = value

        return converted_data

    def create(self, **kwargs):
        data = self.convert_django_names_to_alfresco(kwargs)
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
        # TODO make sure the names match the current names
        converted_kwargs = self.convert_django_names_to_alfresco(kwargs)

        filters = {}

        for key, value in converted_kwargs.items():
            key_bits = key.split("__")
            if len(key_bits) > 1 and key_bits[1] != "exact":
                raise NotImplementedError(
                    "Fields lookups other than exact are not implemented yet."
                )
            filters[key_bits[0]] = value

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
