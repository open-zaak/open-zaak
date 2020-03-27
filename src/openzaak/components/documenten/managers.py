import logging
from decimal import Decimal, InvalidOperation
from privates.storages import private_media_storage
import datetime

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import manager, fields
from django.utils import timezone

from drc_cmis.client import CMISDRCClient, exceptions
from drc_cmis.backend import CMISDRCStorageBackend

from .query import InformatieobjectQuerySet

logger = logging.getLogger(__name__)


def convert_timestamp_to_django_datetime(json_date):
    """
    Takes an int such as 1467717221000 as input and returns 2016-07-05 as output.
    """
    if json_date is not None:
        timestamp = int(str(json_date)[:10])
        django_datetime = timezone.make_aware(datetime.datetime.fromtimestamp(timestamp))
        return django_datetime


def cmis_doc_to_django_model(cmis_doc):
    from .models import EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical

    # The if the document is locked, the lock_id is stored in versionSeriesCheckedOutId
    canonical = EnkelvoudigInformatieObjectCanonical(
        # lock=cmis_doc.versionSeriesCheckedOutId
    )

    versie = cmis_doc.versie
    try:
        int_versie = int(Decimal(versie) * 100)
    except ValueError as e:
        int_versie = 0
    except InvalidOperation:
        int_versie = 0

    # Ensuring the charfields are not null and dates are in the correct format
    for field in EnkelvoudigInformatieObject._meta.get_fields():
        if isinstance(field, fields.CharField) or isinstance(field, fields.TextField):
            if getattr(cmis_doc, field.name) is None:
                setattr(cmis_doc, field.name, '')
        elif isinstance(field, fields.DateTimeField):
            date_value = getattr(cmis_doc, field.name)
            if isinstance(date_value, int):
                setattr(cmis_doc, field.name, convert_timestamp_to_django_datetime(date_value))
        elif isinstance(field, fields.DateField):
            date_value = getattr(cmis_doc, field.name)
            if isinstance(date_value, int):
                converted_datetime = convert_timestamp_to_django_datetime(date_value)
                setattr(cmis_doc, field.name, converted_datetime.date())

    # Setting up a local file with the content of the cmis document
    content_file = File(cmis_doc.get_content_stream())
    content_file.name = cmis_doc.name
    data_in_file = ContentFile(cmis_doc.get_content_stream().read())
    content_file.content = data_in_file
    content_file.path = private_media_storage.save(f'{content_file.name}', data_in_file)

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


class AdapterManager(manager.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return CMISQuerySet(model=self.model, using=self._db, hints=self._hints)
        else:
            return DjangoQuerySet(model=self.model, using=self._db, hints=self._hints)


class DjangoQuerySet(InformatieobjectQuerySet):
    pass


class CMISQuerySet(InformatieobjectQuerySet):
    """
    Find more information about the drc-cmis adapter on github here.
    https://github.com/GemeenteUtrecht/gemma-drc-cmis
    """
    _client = None
    documents = []

    @property
    def get_cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

    def all(self):
        """
        Fetch all the needed results. from the cmis backend.
        """
        logger.debug(f"MANAGER ALL: get_documents start")
        cmis_documents = self.get_cmis_client.get_cmis_documents()
        self.documents = []
        for cmis_doc in cmis_documents['results']:
            self.documents.append(cmis_doc_to_django_model(cmis_doc))

        self._result_cache = self.documents
        logger.debug(f"CMIS_BACKEND: get_documents successful")
        return self

    def iterator(self):
        # loop though the results to return them when requested.
        # Not tested with a filter attached to the all call.
        for document in self.documents:
            yield document

    def create(self, **kwargs):
        # The url needs to be added manually otherwise
        url_informatieobjecttype = kwargs.get('informatieobjecttype')
        kwargs['informatieobjecttype'] = url_informatieobjecttype.get_absolute_api_url()

        # The begin_registratie field needs to be populated (could maybe be moved in cmis library?)
        kwargs['begin_registratie'] = timezone.now()

        cmis_document = self.get_cmis_client.create_document(
            identification=kwargs.get('identificatie'),
            data=kwargs,
            content=kwargs.get('inhoud')
        )

        django_document = cmis_doc_to_django_model(cmis_document)
        return django_document

    def filter(self, *args, **kwargs):
        filters = {}
        #TODO
        # Limit filter to just exact lookup for now (until implemented in drc_cmis)
        for key, value in kwargs.items():
            new_key = key.split("__")
            if len(new_key) > 1 and new_key[1] != "exact":
                raise NotImplementedError("Fields lookups other than exact are not implemented yet.")
            if new_key[0] == 'canonical':
                filters[new_key[0]] = 'Some Value'
            else:
                filters[new_key[0]] = value

        self._result_cache = []

        try:
            if filters.get('identificatie') is not None:
                cmis_doc = self.get_cmis_client.get_cmis_document(
                    identification=filters.get('identificatie'),
                    via_identification=True,
                    filters=None
                )
                self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
            elif filters.get('uuid') is not None:
                cmis_doc = self.get_cmis_client.get_cmis_document(
                    identification=filters.get('uuid'),
                    via_identification=False,
                    filters=None
                )
                self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
            else:
                #Filter the alfresco database
                cmis_documents = self.get_cmis_client.get_cmis_documents(filters=filters)
                for cmis_doc in cmis_documents['results']:
                    self._result_cache.append(cmis_doc_to_django_model(cmis_doc))
        except exceptions.DocumentDoesNotExistError:
            pass

        return self

    # def get(self, *args, **kwargs):
    #     clone = self.filter(*args, **kwargs)
    #     num = len(clone)
    #     if num == 1:
    #         return clone._result_cache[0]
    #     if not num:
    #         raise self.model.DoesNotExist(
    #             "%s matching query does not exist." %
    #             self.model._meta.object_name
    #         )
    #     raise self.model.MultipleObjectsReturned(
    #         "get() returned more than one %s -- it returned %s!" %
    #         (self.model._meta.object_name, num)
    #     )

    def delete(self):

        number_alfresco_updates = 0
        for django_doc in self._result_cache:
            try:
                if settings.CMIS_DELETE_IS_OBLITERATE:
                    # Actually removing the files from Alfresco
                    self.get_cmis_client.obliterate_document(django_doc.uuid)
                else:
                    # Updating all the documents from Alfresco to have 'verwijderd=True'
                    self.get_cmis_client.delete_cmis_document(django_doc.uuid)
                number_alfresco_updates += 1
            except exceptions.DocumentConflictException:
                logger.log(
                    f"Document met identificatie {django_doc.identificatie} kan niet worden gemarkeerd als verwijderd"
                )

        return number_alfresco_updates, {'cmis_document': number_alfresco_updates}

    def update(self, **kwargs):
        cmis_storage = CMISDRCStorageBackend()

        for django_doc in self._result_cache:
            canonical_obj = django_doc.canonical
            canonical_obj.lock_document(
                doc_uuid=django_doc.uuid
            )
            cmis_storage.update_document(
                uuid=django_doc.uuid,
                lock=canonical_obj.lock,
                data=kwargs,
                content=kwargs.get('inhoud'),
            )
            canonical_obj.unlock_document(
                doc_uuid=django_doc.uuid,
                lock=canonical_obj.lock
            )

    #
    # def get_or_create(self, defaults=None, **kwargs):
    #     pass
    #
    # def update_or_create(self, defaults=None, **kwargs):
    #     pass
