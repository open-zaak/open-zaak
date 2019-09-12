import factory

from ...models import StatusType
from .roltype import RolTypeFactory
from .zaaktype import ZaakTypeFactory


class StatusTypeFactory(factory.django.DjangoModelFactory):
    statustypevolgnummer = factory.sequence(lambda n: n + 1)
    zaaktype = factory.SubFactory(ZaakTypeFactory)

    class Meta:
        model = StatusType
