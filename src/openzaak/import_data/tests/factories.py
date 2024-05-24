import datetime
import os
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse

import factory
import factory.fuzzy
from factory.builder import Resolver
from furl import furl
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.utils import generate_unique_identification
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.models.informatieobjecttype import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.constants import (
    ChecksumAlgoritmes,
    OndertekeningSoorten,
    Statussen,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.choices)
    status = ImportStatusChoices.pending

    import_file = factory.django.FileField(filename="import.csv")
    report_file = factory.django.FileField(filename="report.csv")

    class Meta:
        model = Import


def get_informatieobjecttype_url(
    instance: Optional[InformatieObjectType] = None,
) -> str:
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
            version=settings.REST_FRAMEWORK["DEFAULT_VERSION"],
        ),
    )

    return f"{base_url}{instance_url}"


def _get_identificatie(resolver: Resolver) -> str:
    _datetime = datetime.datetime.strptime(resolver.creatiedatum, "%Y-%M-%d")
    instance = EnkelvoudigInformatieObject(creatiedatum=_datetime.date())
    return generate_unique_identification(instance, "creatiedatum")


class DocumentRowFactory(factory.ListFactory):
    uuid = ""
    identificatie = ""

    bronorganisatie = factory.Faker("ssn", locale="nl_NL")
    creatiedatum = str(datetime.date(2018, 6, 27))
    titel = factory.Sequence(lambda count: f"Document {count}")

    vertrouwelijkheidaanduiding = ""

    auteur = factory.Sequence(lambda count: f"Auteur {count}")

    status = ""
    formaat = ""
    taal = "nld"

    bestandsnaam = ""
    bestandsomvang = ""
    bestandspad = ""

    link = ""

    beschrijving = ""
    indicatie_gebruiksrecht = ""
    verschijningsvorm = ""

    ondertekening_soort = ""
    ondertekening_datum = ""

    integriteit_algoritme = ""
    integriteit_waarde = ""
    integriteit_datum = ""

    informatieobjecttype = factory.LazyFunction(get_informatieobjecttype_url)

    zaak_id = ""
    trefwoorden = ""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Simplified version of `FkOrServiceUrlFactoryMixin` with additional
        behavior to an create file for the given `bestandspad`.
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

        if not kwargs["bestandspad"] or kwargs.get("ignore_import_path"):
            return super()._create(model_class, *args, **kwargs)

        path = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR) / kwargs["bestandspad"]
        is_dir = path.is_dir() or kwargs.pop("is_dir", False)

        if is_dir:
            path.mkdir(parents=True)
            return super()._create(model_class, *args, **kwargs)

        if not path.parent.exists():
            os.makedirs(path.parent, exist_ok=True)

        file_content = kwargs.pop("import_file_content", None) or "foobar"
        mode = "wb+" if isinstance(file_content, bytes) else "w+"

        with open(path, mode) as file:
            file.write(file_content)

        return super()._create(model_class, *args, **kwargs)

    class Params:
        with_all_fields = factory.Trait(
            uuid=factory.Faker("uuid4"),
            identificatie=factory.LazyAttribute(
                lambda resolver: _get_identificatie(resolver)
            ),
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar.value,
            status=Statussen.definitief.value,
            formaat="Formaat Y",
            bestandsnaam="foobar.txt",
            bestandsomvang="8092",
            bestandspad="import-test-files/foo.txt",
            beschrijving="a very nice document",
            indicatie_gebruiksrecht="false",
            verschijningsvorm="form XYZ",
            ondertekening_soort=OndertekeningSoorten.analoog.value,
            ondertekening_datum=str(datetime.date(2024, 1, 1)),
            integriteit_algoritme=ChecksumAlgoritmes.crc_16.value,
            integriteit_waarde="foo",
            integriteit_datum=str(datetime.date(2024, 1, 1)),
            trefwoorden='"foo,bar"',
        )
