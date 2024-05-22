import datetime
import os

from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
import factory
from factory.builder import Resolver
import factory.fuzzy
from furl import furl
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.utils import generate_unique_identification
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.models.informatieobjecttype import InformatieObjectType
from openzaak.components.catalogi.tests.factories.informatie_objecten import InformatieObjectTypeFactory
from openzaak.components.documenten.constants import ChecksumAlgoritmes, OndertekeningSoorten, Statussen
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.choices)
    status = ImportStatusChoices.pending

    import_file = factory.django.FileField(filename="import.csv")
    report_file = factory.django.FileField(filename="report.csv")

    class Meta:
        model = Import


def get_informatieobjecttype_url(instance: Optional[InformatieObjectType] = None) -> str:
    try:
        informatieobjecttype = InformatieObjectType.objects.first()
    except InformatieObjectType.DoesNotExist:
        informatieobjecttype = InformatieObjectTypeFactory()

    site = Site.objects.get()

    base_url = f"https://{site.domain}"
    instance_url = reverse(
        "informatieobjecttype-detail",
        kwargs=dict(
            uuid=informatieobjecttype.uuid,
            version=settings.REST_FRAMEWORK["DEFAULT_VERSION"]
        ),
    )

    return f"{base_url}{instance_url}"


def _identificatie(resolver: Resolver) -> str:
    _datetime = datetime.datetime.strptime(resolver.creatiedatum, "%Y-%M-%d")
    instance = EnkelvoudigInformatieObject(creatiedatum=_datetime.date())
    return generate_unique_identification(instance, "creatiedatum")


class DocumentRowFactory(factory.ListFactory):
    uuid = factory.Faker("uuid4")
    identificatie = factory.LazyAttribute(lambda resolver: _identificatie(resolver))

    bronorganisatie = factory.Faker("ssn", locale="nl_NL")
    creatiedatum = str(datetime.date(2018, 6, 27))
    titel = factory.Sequence(lambda count: f"Document {count}")

    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar.value

    auteur = factory.Sequence(lambda count: f"Auteur {count}")

    status = Statussen.definitief.value
    formaat = "Formaat Y"
    taal = "nld"

    bestandsnaam = "foo.txt"
    bestandsomvang = "8092"
    bestandspad = "some/path/foo.txt"

    link = ""

    beschrijving = "a very nice document"
    indicatie_gebruiksrecht = "false"
    verschijningsvorm = ""

    ondertekening_soort = OndertekeningSoorten.analoog.value
    ondertekening_datum = factory.LazyFunction(
        lambda: str(datetime.date(2024, 1, 1))
    )

    integriteit_algoritme = ChecksumAlgoritmes.crc_16.value
    integriteit_waarde = "foo"
    integriteit_datum = str(datetime.date(2024, 1, 1))

    informatieobjecttype = factory.LazyFunction(get_informatieobjecttype_url)

    zaak_id = ""
    trefwoorden = ""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Simplified version of `FkOrServiceUrlFactoryMixin`
        """
        services = []

        service_fields = ("informatieobjecttype",)

        for field in kwargs:
            if field not in service_fields:
                continue

            value = kwargs[field]

            if not value:
                continue

            base_url = furl(value).origin
            services.append(Service(api_root=base_url, api_type=APITypes.orc))

        Service.objects.bulk_create(services, ignore_conflicts=True)

        file_path = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR) / kwargs["bestandspad"]

        if not file_path.exists():
            os.makedirs(file_path.parent)

        with open(file_path, "w+") as file:
            file.write("foo")

        return super()._create(model_class, *args, **kwargs)
