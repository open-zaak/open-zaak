import factory
import factory.fuzzy

from openzaak.import_data.models import Import, ImportStatusChoices, ImportTypeChoices


class ImportFactory(factory.django.DjangoModelFactory):
    import_type = factory.fuzzy.FuzzyChoice(ImportTypeChoices.choices)
    status = ImportStatusChoices.pending

    import_file = factory.django.FileField(filename="import.csv")
    report_file = factory.django.FileField(filename="report.csv")

    class Meta:
        model = Import


# TODO: WIP factory
class DocumentRowFactory(factory.ListFactory):
    identificatie = factory.LazyFunction()  # TODO: use `generate_unique_identification`
    bronorganisatie = factory.Faker()
    creatiedatum = factory.Faker()
    titel = factory.Faker()
    vertrouwelijkheidaanduiding = factory.Faker()
    auteur = factory.Faker()
    status = factory.Faker()
    formaat = factory.Faker()
    taal = factory.Faker()

    bestandsnaam = factory.Faker()
    bestandsomvang = factory.Faker()
    bestandspad = factory.Faker()

    link = factory.Faker()
    beschrijving = factory.Faker()
    indicatie_gebruiksrecht = factory.Faker()
    verschijningsvorm = factory.Faker()

    ondertekening_soort = factory.Faker()
    ondertekening_datum = factory.Faker()

    integriteit_algoritme = factory.Faker()
    integriteit_waarde = factory.Faker()
    integriteit_datum = factory.Faker()

    informatieobjecttype = factory.Faker()

    zaak_id = ""
    trefwoorden = ""
