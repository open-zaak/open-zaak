# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Factory models for the documenten application.

.. note::
    There is no ObjectInformatieObjectFactory anymore, since that is
    created automatically as part of
    :class:`openzaak.components.zaken.models.ZaakInformatieObject` and
    :class:`openzaak.components.besluiten.models.BesluitInformatieObject`
    creation.
"""
import datetime
import os
import string
from pathlib import Path

from django.conf import settings
from django.test import RequestFactory

import factory
import factory.fuzzy
from factory.builder import Resolver
from furl import furl
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.utils import generate_unique_identification
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.import_data.models import ImportRowResultChoices
from openzaak.import_data.tests.factories import get_informatieobjecttype_url
from openzaak.tests.utils import FkOrServiceUrlFactoryMixin

from ..constants import (
    AfzenderTypes,
    ChecksumAlgoritmes,
    OndertekeningSoorten,
    PostAdresTypes,
    Statussen,
)
from ..models import BestandsDeel, EnkelvoudigInformatieObject


class EnkelvoudigInformatieObjectCanonicalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "documenten.EnkelvoudigInformatieObjectCanonical"

    latest_version = factory.RelatedFactory(
        "openzaak.components.documenten.tests.factories.EnkelvoudigInformatieObjectFactory",
        "canonical",
    )


class EnkelvoudigInformatieObjectFactory(
    FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory
):
    canonical = factory.SubFactory(
        EnkelvoudigInformatieObjectCanonicalFactory, latest_version=None
    )
    identificatie = factory.Sequence(lambda n: f"document-{n}")
    bronorganisatie = factory.Faker("ssn", locale="nl_NL")
    creatiedatum = datetime.date(2018, 6, 27)
    titel = "some titel"
    auteur = "some auteur"
    formaat = "some formaat"
    taal = "nld"
    inhoud = factory.django.FileField(
        data=b"some data", filename=factory.Sequence(lambda n: f"file-{n}.bin")
    )
    bestandsomvang = factory.LazyAttribute(lambda o: o.inhoud.size)
    informatieobjecttype = factory.SubFactory(InformatieObjectTypeFactory)
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar

    class Meta:
        model = "documenten.EnkelvoudigInformatieObject"

    @classmethod
    def create(cls, **kwargs):
        # for DRC-CMIS, we pass in a request object containing the correct host.
        # This way, we don't have to set up the sites framework for every test (case).
        # The result is that informatieobjecttype has the correct URL reference in CMIS.
        kwargs["_request"] = RequestFactory().get("/")
        return super().create(**kwargs)


class GebruiksrechtenFactory(factory.django.DjangoModelFactory):
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)
    omschrijving_voorwaarden = factory.Faker("paragraph")

    class Meta:
        model = "documenten.Gebruiksrechten"

    @factory.lazy_attribute
    def startdatum(self):
        return datetime.datetime.combine(
            self.informatieobject.latest_version.creatiedatum, datetime.time(0, 0)
        ).replace(tzinfo=datetime.timezone.utc)


class GebruiksrechtenCMISFactory(factory.django.DjangoModelFactory):
    startdatum = datetime.datetime.now(tz=datetime.timezone.utc)
    omschrijving_voorwaarden = factory.Faker("paragraph")

    class Meta:
        model = "documenten.Gebruiksrechten"


class BestandsDeelFactory(factory.django.DjangoModelFactory):
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)
    inhoud = factory.django.FileField(data=b"some data", filename="file_part.bin")
    omvang = factory.LazyAttribute(lambda o: o.inhoud.size)

    class Meta:
        model = "documenten.BestandsDeel"

    @factory.lazy_attribute
    def volgnummer(self) -> int:
        # note that you need to use create to get an accurate count of other created
        # instances.
        io_uuid = getattr(self, "informatieobject_uuid", None)
        existing_bestandsdelen = (
            BestandsDeel.objects.filter(informatieobject_uuid=io_uuid)
            if io_uuid
            else self.informatieobject.bestandsdelen
        )
        return existing_bestandsdelen.count() + 1


class VerzendingFactory(factory.django.DjangoModelFactory):
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)
    betrokkene = factory.Faker("url")
    aard_relatie = factory.fuzzy.FuzzyChoice(AfzenderTypes.values)
    contact_persoon = factory.Faker("url")

    class Meta:
        model = "documenten.Verzending"

    class Params:
        has_inner_address = factory.Trait(
            binnenlands_correspondentieadres_huisnummer=factory.fuzzy.FuzzyInteger(
                low=1, high=100
            ),
            binnenlands_correspondentieadres_naam_openbare_ruimte=factory.Faker(
                "city", locale="nl_NL"
            ),
            binnenlands_correspondentieadres_woonplaatsnaam=factory.Faker(
                "city", locale="nl_NL"
            ),
        )
        has_outer_address = factory.Trait(
            buitenlands_correspondentieadres_adres_buitenland_1=factory.fuzzy.FuzzyText(
                length=35
            ),
            buitenlands_correspondentieadres_land_postadres=factory.Faker("url"),
        )
        has_post_address = factory.Trait(
            correspondentie_postadres_postbus_of_antwoord_nummer=factory.fuzzy.FuzzyInteger(
                low=1, high=9999
            ),
            correspondentie_postadres_postcode=factory.Faker(
                "pystr_format", string_format="%###??", letters=string.ascii_uppercase
            ),
            correspondentie_postadres_postadrestype=factory.fuzzy.FuzzyChoice(
                PostAdresTypes.values
            ),
            correspondentie_postadres_woonplaatsnaam=factory.Faker(
                "city", locale="nl_NL"
            ),
        )


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
    ontvangstdatum = ""
    verzenddatum = ""
    indicatie_gebruiksrecht = ""
    verschijningsvorm = ""

    ondertekening_soort = ""
    ondertekening_datum = ""

    integriteit_algoritme = ""
    integriteit_waarde = ""
    integriteit_datum = ""

    informatieobjecttype = factory.LazyFunction(get_informatieobjecttype_url)

    zaak_uuid = ""
    trefwoorden = ""

    @classmethod
    def _create_file(cls, model_class, *args, **kwargs):
        base_dir = Path(settings.IMPORT_DOCUMENTEN_BASE_DIR)

        if not base_dir.exists():
            base_dir.mkdir(parents=True)

        path = base_dir / kwargs["bestandspad"]

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

        return cls._create_file(model_class, *args, **kwargs)

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
            ontvangstdatum=str(datetime.date(2024, 1, 1)),
            verzenddatum=str(datetime.date(2024, 1, 1)),
            indicatie_gebruiksrecht="false",
            verschijningsvorm="form XYZ",
            ondertekening_soort=OndertekeningSoorten.analoog.value,
            ondertekening_datum=str(datetime.date(2024, 1, 1)),
            integriteit_algoritme=ChecksumAlgoritmes.crc_16.value,
            integriteit_waarde="foo",
            integriteit_datum=str(datetime.date(2024, 1, 1)),
            trefwoorden='"foo,bar"',
        )


class DocumentRowReportFactory(DocumentRowFactory):
    comment = ""
    resultaat = factory.fuzzy.FuzzyChoice(ImportRowResultChoices.labels)
