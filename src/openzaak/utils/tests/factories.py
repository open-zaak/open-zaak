import factory
import factory.fuzzy

from openzaak.utils.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.choices)
    status = ImportStatusChoices.pending

    import_file = factory.django.FileField(filename="import.csv")
    report_file = factory.django.FileField(filename="report.csv")

    class Meta:
        model = Import
