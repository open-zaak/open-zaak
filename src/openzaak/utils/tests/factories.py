import factory
import factory.fuzzy

from openzaak.utils.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.choices)
    status = ImportStatusChoices.pending

    class Meta:
        model = Import
