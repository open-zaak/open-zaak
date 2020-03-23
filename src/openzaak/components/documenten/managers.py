import logging
from decimal import Decimal, InvalidOperation
from privates.storages import private_media_storage

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import manager, fields

from drc_cmis.client import CMISDRCClient, exceptions

from .query import InformatieobjectQuerySet

logger = logging.getLogger(__name__)


def convert_timestamp_to_django_date(json_date):
    """
    Takes an int such as 1467717221000 as input and returns 2016-07-05 as output.
    """
    if json_date is not None:
        import datetime
        timestamp = int(str(json_date)[:10])
        django_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        return django_date


def cmis_doc_to_django_model(cmis_doc):
    from .models import EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical

    if cmis_doc.versionSeriesCheckedOutId is None:
        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()
    else:
        canonical = EnkelvoudigInformatieObjectCanonical.objects.create(cmis_doc=cmis_doc)

    versie = cmis_doc.versie
    try:
        int_versie = int(Decimal(versie) * 100)
    except ValueError as e:
        int_versie = 0
    except InvalidOperation:
        int_versie = 0

    date_fields = ['creatiedatum', 'ontvangstdatum', 'verzenddatum']
    for date_field in date_fields:
        date_value = getattr(cmis_doc, date_field)
        if isinstance(date_value, int):
            setattr(cmis_doc, date_field, convert_timestamp_to_django_date(date_value))

    # Ensuring the charfields are not null
    for field in EnkelvoudigInformatieObject._meta.get_fields():
        if isinstance(field, fields.CharField) or isinstance(field, fields.TextField):
            if getattr(cmis_doc, field.name) is None:
                setattr(cmis_doc, field.name, '')

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


class CanonicalAdapterManager(manager.Manager):
    def get_queryset(self):
        if settings.CMIS_ENABLED:
            return CMISCanonicalQuerySet(model=self.model, using=self._db, hints=self._hints)
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
        Fetch all the needed resutls. from the cmis backend.
        """
        logger.debug(f"MANAGER ALL: get_documents start")
        cmis_documents = self.get_cmis_client.get_cmis_documents()
        self.documents = []
        for cmis_doc in cmis_documents['results']:
            self.documents.append(cmis_doc_to_django_model(cmis_doc))

        logger.debug(f"CMIS_BACKEND: get_documents successful")
        return self

    def iterator(self):
        # loop though the results to retrurn them when requested.
        # Not tested with a filter attached to the all call.
        for document in self.documents:
            yield document

    def create(self, **kwargs):
        cmis_document = self.get_cmis_client.create_document(
            identification=kwargs.get('identificatie'),
            data=kwargs,
            content=kwargs.get('inhoud')
        )

        #TODO fix cmis_doc_to_django_model()
        # django_document = self.model(**kwargs)
        # django_document.uuid = cmis_document.versionSeriesId
        # django_document.save()
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

    def delete(self):
        # Updating all the documents from Alfresco to have 'verwijderd=True'
        number_alfresco_updates = 0
        for cmis_doc in self._result_cache:
            try:
                self.get_cmis_client.delete_cmis_document(cmis_doc.uuid)
                number_alfresco_updates += 1
            except exceptions.DocumentConflictException:
                logger.log(
                    f"Document met identificatie {cmis_doc.identificatie} kan niet worden gemarkeerd als verwijderd"
                )

        return number_alfresco_updates, {'cmis_document': number_alfresco_updates}

    def obliterate(self):
        # This actually removes the documents from alfresco
        number_alfresco_updates = 0
        for cmis_doc in self._result_cache:
            try:
                self.get_cmis_client.obliterate_document(cmis_doc.uuid)
                number_alfresco_updates += 1
            except exceptions.DocumentConflictException:
                logger.log(
                    f"Document met identificatie {cmis_doc.identificatie} kan niet worden verwijderd"
                )

        return number_alfresco_updates, {'cmis_document': number_alfresco_updates}

    # def update(self):
    #     pass
    #
    # def get_or_create(self, defaults=None, **kwargs):
    #     pass
    #
    # def update_or_create(self, defaults=None, **kwargs):
    #     pass


class CMISCanonicalQuerySet(InformatieobjectQuerySet):

    _client = None

    @property
    def get_cmis_client(self):
        if not self._client:
            self._client = CMISDRCClient()

        return self._client

    def create(self, **kwargs):

        cmis_doc = kwargs.get('cmis_doc')
        if cmis_doc is not None:
            lock_id = cmis_doc.versionSeriesCheckedOutId.split(";")[0]
            return super().create(lock=lock_id)
        else:
            return super().create(**kwargs)
