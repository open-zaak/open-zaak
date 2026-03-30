# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from datetime import date, timezone

from django.db.models.signals import post_save

import factory
import factory.fuzzy
from vng_api_common.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)

from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
)
from openzaak.tests.utils import FkOrServiceUrlFactoryMixin

from ..constants import AardZaakRelatie
from ..signals import (
    send_resultaat_zaak_gemuteerd_event,
    send_status_zaak_gemuteerd_event,
    send_substatus_zaak_gemuteerd_event,
    send_zaak_gemuteerd_event,
    send_zio_zaak_gemuteerd_event,
)


class MuteReceiverFactoryMixin:
    _muted_receivers = []  # [(signal, receiver, sender, dispatch_uid)]

    @classmethod
    def _generate(cls, strategy, params):
        disconnected = []

        for signal, receiver, sender, dispatch_uid in cls._muted_receivers:
            sender_class = cls._load_model_class(sender)
            if signal.disconnect(
                receiver, sender=sender_class, dispatch_uid=dispatch_uid
            ):
                disconnected.append((signal, receiver, sender_class, dispatch_uid))

        try:
            result = super()._generate(strategy, params)
        finally:
            for signal, receiver, sender, dispatch_uid in disconnected:
                signal.connect(receiver, sender=sender, dispatch_uid=dispatch_uid)
        return result


class ZaakFactory(
    MuteReceiverFactoryMixin,
    FkOrServiceUrlFactoryMixin,
    factory.django.DjangoModelFactory,
):
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(
        choices=VertrouwelijkheidsAanduiding.values
    )
    registratiedatum = factory.Faker("date_this_month", before_today=True)
    startdatum = factory.Faker("date_this_month", before_today=True)
    bronorganisatie = factory.Faker("ssn", locale="nl_NL")
    verantwoordelijke_organisatie = factory.Faker("ssn", locale="nl_NL")

    _muted_receivers = [
        (
            post_save,
            send_zaak_gemuteerd_event,
            "zaken.Zaak",
            "zaken.zaak.send_zaak_gemuteerd_event",
        )
    ]

    class Meta:
        model = "zaken.Zaak"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )
        closed = factory.Trait(
            einddatum=factory.LazyFunction(date.today),
            status_set=factory.RelatedFactory(
                "openzaak.components.zaken.tests.factories.StatusFactory",
                factory_related_name="zaak",
                statustype__zaaktype=factory.SelfAttribute("..zaak.zaaktype"),
            ),
        )


class RelevanteZaakRelatieFactory(
    FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory
):
    zaak = factory.SubFactory(ZaakFactory)
    url = factory.SubFactory(ZaakFactory)
    aard_relatie = AardZaakRelatie.vervolg

    class Meta:
        model = "zaken.RelevanteZaakRelatie"


class ZaakRelatieFactory(FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    url = factory.SubFactory(ZaakFactory)

    class Meta:
        model = "zaken.ZaakRelatie"


class ZaakInformatieObjectFactory(
    MuteReceiverFactoryMixin,
    FkOrServiceUrlFactoryMixin,
    factory.django.DjangoModelFactory,
):
    zaak = factory.SubFactory(ZaakFactory)
    informatieobject = factory.SubFactory(EnkelvoudigInformatieObjectCanonicalFactory)

    _muted_receivers = [
        (
            post_save,
            send_zio_zaak_gemuteerd_event,
            "zaken.ZaakInformatieObject",
            "zaken.zio.send_zaak_gemuteerd_event",
        )
    ]

    class Meta:
        model = "zaken.ZaakInformatieObject"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


class ZaakEigenschapFactory(
    FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory
):
    zaak = factory.SubFactory(ZaakFactory)
    eigenschap = factory.SubFactory(
        EigenschapFactory, zaaktype=factory.SelfAttribute("..zaak.zaaktype")
    )
    _naam = factory.Faker("word")
    waarde = factory.Faker("word")

    class Meta:
        model = "zaken.ZaakEigenschap"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


class ZaakObjectFactory(FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    object = factory.Faker("url")
    # Excluded: overige
    object_type = factory.fuzzy.FuzzyChoice(choices=list(ZaakobjectTypes.values)[:-1])

    class Meta:
        model = "zaken.ZaakObject"


class WozWaardeFactory(factory.django.DjangoModelFactory):
    zaakobject = factory.SubFactory(ZaakObjectFactory)

    class Meta:
        model = "zaken.WozWaarde"


class RolFactory(FkOrServiceUrlFactoryMixin, factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    betrokkene = factory.Faker("url")
    betrokkene_type = factory.fuzzy.FuzzyChoice(RolTypes.values)
    roltype = factory.SubFactory(RolTypeFactory)
    omschrijving = factory.Faker("word")
    omschrijving_generiek = factory.fuzzy.FuzzyChoice(RolOmschrijving.values)

    class Meta:
        model = "zaken.Rol"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


class StatusFactory(
    MuteReceiverFactoryMixin,
    FkOrServiceUrlFactoryMixin,
    factory.django.DjangoModelFactory,
):
    zaak = factory.SubFactory(ZaakFactory)
    statustype = factory.SubFactory(StatusTypeFactory)
    datum_status_gezet = factory.Faker("date_time_this_month", tzinfo=timezone.utc)

    _muted_receivers = [
        (
            post_save,
            send_status_zaak_gemuteerd_event,
            "zaken.Status",
            "zaken.status.send_zaak_gemuteerd_event",
        )
    ]

    class Meta:
        model = "zaken.Status"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


class ResultaatFactory(
    MuteReceiverFactoryMixin,
    FkOrServiceUrlFactoryMixin,
    factory.django.DjangoModelFactory,
):
    zaak = factory.SubFactory(ZaakFactory)
    resultaattype = factory.SubFactory(
        ResultaatTypeFactory,
        zaaktype=factory.SelfAttribute("..zaak.zaaktype"),
    )

    _muted_receivers = [
        (
            post_save,
            send_resultaat_zaak_gemuteerd_event,
            "zaken.Resultaat",
            "zaken.resultaat.send_zaak_gemuteerd_event",
        )
    ]

    class Meta:
        model = "zaken.Resultaat"

    class Params:
        with_etag = factory.Trait(
            _etag=factory.PostGenerationMethodCall("calculate_etag_value")
        )


# @factory.django.mute_signals(post_save)
class SubStatusFactory(MuteReceiverFactoryMixin, factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    status = factory.SubFactory(StatusFactory)
    tijdstip = factory.Faker("date_time_this_month", tzinfo=timezone.utc)

    _muted_receivers = [
        (
            post_save,
            send_substatus_zaak_gemuteerd_event,
            "zaken.SubStatus",
            "zaken.substatus.send_zaak_gemuteerd_event",
        )
    ]

    class Meta:
        model = "zaken.SubStatus"


class KlantContactFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    identificatie = factory.Sequence(lambda n: f"{n}")
    datumtijd = factory.Faker("date_time_this_month", tzinfo=timezone.utc)

    class Meta:
        model = "zaken.KlantContact"


class ZaakContactMomentFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    contactmoment = factory.Faker("url")

    class Meta:
        model = "zaken.ZaakContactMoment"


class ZaakVerzoekFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    verzoek = factory.Faker("url")

    class Meta:
        model = "zaken.ZaakVerzoek"


class ZaakKenmerkFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    kenmerk = factory.Faker("word")
    bron = factory.Faker("word")

    class Meta:
        model = "zaken.ZaakKenmerk"


class ZaakNotitieFactory(factory.django.DjangoModelFactory):
    gerelateerd_aan = factory.SubFactory(ZaakFactory)
    onderwerp = factory.Faker("sentence")
    tekst = factory.Faker("paragraph")
    aangemaakt_door = factory.Faker("name")

    class Meta:
        model = "zaken.ZaakNotitie"
