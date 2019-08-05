import factory

from ....models import CheckListItem, StatusType
from .roltype import RolTypeFactory
from .zaken import ZaakTypeFactory


class CheckListItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CheckListItem


class StatusTypeFactory(factory.django.DjangoModelFactory):
    statustypevolgnummer = factory.sequence(lambda n: n + 1)
    zaaktype = factory.SubFactory(ZaakTypeFactory)

    class Meta:
        model = StatusType

    @factory.post_generation
    def roltypen(self, create, extracted, **kwargs):
        # optional M2M, do nothing when no arguments are passed
        if not extracted:
            extracted = [RolTypeFactory.create(zaaktype=self.zaaktype)]

        for roltype in extracted:
            self.roltypen.add(roltype)
