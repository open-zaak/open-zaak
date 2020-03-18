import logging
from decimal import Decimal

from django.conf import settings
from django.db.models import manager

from drc_cmis.client import CMISDRCClient

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
    from .models import EnkelvoudigInformatieObject

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

    document = EnkelvoudigInformatieObject(
        auteur=cmis_doc.auteur,
        begin_registratie=cmis_doc.begin_registratie,
        beschrijving=cmis_doc.beschrijving,
        bestandsnaam=cmis_doc.bestandsnaam,
        bronorganisatie=cmis_doc.bronorganisatie,
        creatiedatum=cmis_doc.creatiedatum,
        formaat=cmis_doc.formaat,
        id=cmis_doc.versionSeriesId,
        identificatie=cmis_doc.identificatie,
        indicatie_gebruiksrecht=cmis_doc.indicatie_gebruiksrecht,
        informatieobjecttype=cmis_doc.informatieobjecttype,
        inhoud="",
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
        django_document = super().create(**kwargs)
        django_document.uuid = cmis_document.versionSeriesId
        django_document.save()
        return django_document

    def get(self, *args, **kwargs):
        """
        Gets the documents from the cmis backend through the identificatie or uuid fields.
        """
        django_documents = []

        if kwargs.get('identificatie') is not None:
            cmis_doc = self.get_cmis_client.get_cmis_document(
                identification=kwargs.get('identificatie'),
                via_identification=True,
                filters=None
            )
            # Check if a model with that identificatie already exists in the ORM otherwise create it
            documents_in_orm = self.filter(identificatie=kwargs.get('identificatie'))

        elif kwargs.get('uuid') is not None:
            cmis_doc = self.get_cmis_client.get_cmis_document(
                identification=kwargs.get('uuid'),
                via_identification=False,
                filters=None
            )
            # Check if a model with that uuid already exists in the ORM otherwise create it
            documents_in_orm = self.filter(uuid=kwargs.get('uuid'))
        else:
            # TODO
            raise NotImplementedError("Getting with filters other than uuid and identificatie to be implemented.")

        if documents_in_orm.count() == 0:
            django_documents.append(cmis_doc_to_django_model(cmis_doc))
        else:
            for doc in documents_in_orm:
                django_documents.append(doc)

        if len(django_documents) == 1:
            return django_documents[0]
        elif len(django_documents) == 0:
            raise self.model.DoesNotExist(
                "%s matching query does not exist." %
                self.model._meta.object_name
            )
        else:
            raise self.model.MultipleObjectsReturned(
                "get() returned more than one %s -- it returned %s!" %
                (self.model._meta.object_name, len(self.documents))
            )

    # def delete(self):
    #     pass

    # def filter(self):
    #     pass

    # def delete(self):
    #     pass
    #
    # def update(self):
    #     pass
    #
    # def get_or_create(self, defaults=None, **kwargs):
    #     pass
    #
    # def update_or_create(self, defaults=None, **kwargs):
    #     pass
