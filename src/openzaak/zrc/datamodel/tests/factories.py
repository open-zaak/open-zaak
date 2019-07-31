from django.utils import timezone

import factory
import factory.fuzzy
from vng_api_common.constants import (
    RolOmschrijving, RolTypes, VertrouwelijkheidsAanduiding, ZaakobjectTypes
)


class ZaakFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.Faker('url')
    vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(choices=VertrouwelijkheidsAanduiding.values)
    registratiedatum = factory.Faker('date_this_month', before_today=True)
    startdatum = factory.Faker('date_this_month', before_today=True)
    bronorganisatie = factory.Faker('ssn', locale='nl_NL')
    verantwoordelijke_organisatie = factory.Faker('ssn', locale='nl_NL')

    class Meta:
        model = 'datamodel.Zaak'


class ZaakInformatieObjectFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    informatieobject = factory.Faker('url')

    class Meta:
        model = 'datamodel.ZaakInformatieObject'


class ZaakEigenschapFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    eigenschap = factory.Faker('url')
    _naam = factory.Faker('word')
    waarde = factory.Faker('word')

    class Meta:
        model = 'datamodel.ZaakEigenschap'


class ZaakObjectFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    object = factory.Faker('url')
    # Excluded: overige
    object_type = factory.fuzzy.FuzzyChoice(choices=list(ZaakobjectTypes.values)[:-1])

    class Meta:
        model = 'datamodel.ZaakObject'


class RolFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    betrokkene = factory.Faker('url')
    betrokkene_type = factory.fuzzy.FuzzyChoice(RolTypes.values)
    roltype = factory.Faker('url')
    omschrijving = factory.Faker('word')
    omschrijving_generiek = factory.fuzzy.FuzzyChoice(RolOmschrijving.values)

    class Meta:
        model = 'datamodel.Rol'


class StatusFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    statustype = factory.Faker('url')
    datum_status_gezet = factory.Faker('date_time_this_month', tzinfo=timezone.utc)

    class Meta:
        model = 'datamodel.Status'


class ResultaatFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    resultaattype = factory.Faker('url')

    class Meta:
        model = 'datamodel.Resultaat'


class KlantContactFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    identificatie = factory.Sequence(lambda n: f'{n}')
    datumtijd = factory.Faker('date_time_this_month', tzinfo=timezone.utc)

    class Meta:
        model = 'datamodel.KlantContact'


class ZaakBesluitFactory(factory.django.DjangoModelFactory):
    zaak = factory.SubFactory(ZaakFactory)
    besluit = factory.Faker('url')

    class Meta:
        model = 'datamodel.ZaakBesluit'
