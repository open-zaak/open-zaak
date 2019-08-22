from unittest import skip

from django.test import TestCase

from openzaak.components.catalogi.models import (
    InformatieObjectType,
    ResultaatType,
    ZaakInformatieobjectType,
    ZaakInformatieobjectTypeArchiefregime,
    ZaakType,
    ZaakTypenRelatie,
)

from .factories import (
    BesluitTypeFactory,
    BronCatalogusFactory,
    BronZaakTypeFactory,
    CatalogusFactory,
    CheckListItemFactory,
    EigenschapFactory,
    EigenschapReferentieFactory,
    EigenschapSpecificatieFactory,
    FormulierFactory,
    InformatieObjectTypeFactory,
    InformatieObjectTypeOmschrijvingGeneriekFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypenRelatieFactory,
)


class FactoryTests(TestCase):
    def test_factories(self):
        iot = InformatieObjectTypeFactory.create()

        self.assertIsNotNone(iot.omschrijving_generiek_id)
        self.assertIsNotNone(iot.catalogus_id)

        InformatieObjectTypeOmschrijvingGeneriekFactory.create()

        EigenschapSpecificatieFactory.create()
        EigenschapReferentieFactory.create()
        CatalogusFactory.create()
        EigenschapFactory.create()
        BesluitTypeFactory.create()
        # self.assertIsNotNone(besluit_type.wordt_vastgelegd_in)
        # self.assertIsNotNone(besluit_type.zaaktypes)
        # self.assertIsNotNone(besluit_type.is_resultaat_van)

        ResultaatTypeFactory.create()
        RolTypeFactory.create()
        ZaakObjectTypeFactory.create()
        FormulierFactory.create()
        BronCatalogusFactory.create()
        BronZaakTypeFactory.create()
        CheckListItemFactory.create()
        StatusTypeFactory.create()
        ZaakTypeFactory.create()

    def test_informatieobjecttype_factory(self):
        self.assertEqual(InformatieObjectType.objects.count(), 0)
        self.assertEqual(ZaakInformatieobjectType.objects.count(), 0)
        self.assertEqual(ZaakType.objects.count(), 0)

        InformatieObjectTypeFactory.create()

        self.assertEqual(InformatieObjectType.objects.count(), 1)
        self.assertEqual(ZaakInformatieobjectType.objects.count(), 1)
        self.assertEqual(ZaakType.objects.count(), 1)

    @skip("ZaakInformatieobjectTypeArchiefregime is disabled at the moment")
    def test_zaak_informatieobject_type_archiefregime_factory(self):
        self.assertEqual(ResultaatType.objects.count(), 0)
        self.assertEqual(ZaakInformatieobjectTypeArchiefregime.objects.count(), 0)
        self.assertEqual(ZaakInformatieobjectType.objects.count(), 0)

        ResultaatTypeFactory.create()

        self.assertEqual(ResultaatType.objects.count(), 1)
        self.assertEqual(ZaakInformatieobjectTypeArchiefregime.objects.count(), 1)
        # TODO: we might want to enforce that the same ZIT will be used. they currently belong to different ZaakTypes
        self.assertEqual(ZaakInformatieobjectType.objects.count(), 1)

        ResultaatTypeFactory.create(bepaalt_afwijkend_archiefregime_van=None)
        self.assertEqual(ResultaatType.objects.count(), 2)  # + 1
        self.assertEqual(
            ZaakInformatieobjectTypeArchiefregime.objects.count(), 1
        )  # stays the same
        self.assertEqual(ZaakInformatieobjectType.objects.count(), 1)  # stay the same

    def test_zaak_typen_relatie_factory(self):
        self.assertEqual(ZaakType.objects.count(), 0)
        self.assertEqual(ZaakTypenRelatie.objects.count(), 0)

        zaaktype1 = ZaakTypeFactory.create()

        self.assertEqual(ZaakType.objects.count(), 1)
        self.assertEqual(ZaakTypenRelatie.objects.count(), 0)

        ZaakTypenRelatieFactory.create(zaaktype=zaaktype1)
        self.assertEqual(ZaakType.objects.count(), 1)
        self.assertEqual(ZaakTypenRelatie.objects.count(), 1)

        self.assertEqual(zaaktype1.zaaktypenrelaties.count(), 1)
