import factory
import factory.fuzzy

from ...constants import AardRelatieChoices, RichtingChoices
from ...models import (
    ZaakTypeInformatieObjectType,
    ZaakTypeInformatieObjectTypeArchiefregime,
    ZaakTypenRelatie,
)


class ZaakTypeInformatieObjectTypeFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.SubFactory(
        "openzaak.components.catalogi.tests.factories.ZaakTypeFactory"
    )
    informatieobjecttype = factory.SubFactory(
        "openzaak.components.catalogi.tests.factories.InformatieObjectTypeFactory",
        zaaktypen=None,
    )
    volgnummer = factory.sequence(lambda x: x)
    richting = RichtingChoices.inkomend

    class Meta:
        model = ZaakTypeInformatieObjectType


class ZaakTypeInformatieObjectTypeArchiefregimeFactory(factory.django.DjangoModelFactory):
    zaak_informatieobject_type = factory.SubFactory(ZaakTypeInformatieObjectTypeFactory)
    resultaattype = factory.SubFactory(
        "openzaak.components.catalogi.tests.factories.ResultaatTypeFactory"
    )
    archiefactietermijn = 7

    class Meta:
        model = ZaakTypeInformatieObjectTypeArchiefregime


class ZaakTypenRelatieFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.SubFactory(
        "openzaak.components.catalogi.tests.factories.ZaakTypeFactory"
    )
    gerelateerd_zaaktype = factory.Faker("url")
    aard_relatie = factory.fuzzy.FuzzyChoice(choices=AardRelatieChoices.values)

    class Meta:
        model = ZaakTypenRelatie
