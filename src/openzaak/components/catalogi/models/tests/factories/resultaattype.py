import factory
import factory.fuzzy
from dateutil.relativedelta import relativedelta

from ....models import ResultaatType
from .zaken import ZaakTypeFactory


class ResultaatTypeFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.SubFactory(ZaakTypeFactory)
    omschrijving = factory.Faker('word', locale='nl')
    resultaattypeomschrijving = factory.Faker('url')
    omschrijving_generiek = factory.Faker('word')
    selectielijstklasse = factory.Faker('url')
    archiefnominatie = factory.fuzzy.FuzzyChoice(['blijvend_bewaren', 'vernietigen'])
    archiefactietermijn = relativedelta(years=10)

    class Meta:
        model = ResultaatType
