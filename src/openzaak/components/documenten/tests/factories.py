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
import string

from django.test import RequestFactory
from django.utils import timezone

import factory
import factory.fuzzy
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import FkOrServiceUrlFactoryMixin

from ..constants import AfzenderTypes, PostAdresTypes
from ..models import BestandsDeel


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
    inhoud = factory.django.FileField(data=b"some data", filename="file.bin")
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
        ).replace(tzinfo=timezone.utc)


class GebruiksrechtenCMISFactory(factory.django.DjangoModelFactory):
    startdatum = datetime.datetime.now(tz=timezone.utc)
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
            buitenlands_correspondentieadres_adres_buitenland_1=factory.Faker(
                "street_address"
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
