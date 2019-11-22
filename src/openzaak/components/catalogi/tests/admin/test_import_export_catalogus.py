import os

from django.urls import reverse

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import (
    BesluitType,
    Catalogus,
    Eigenschap,
    InformatieObjectType,
    RolType,
    StatusType,
    ZaakInformatieobjectType,
    ZaakType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakInformatieobjectTypeFactory,
    ZaakTypeFactory,
)


class CatalogusAdminImportExportTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)
        self.filename = "TEST.zip"

    def test_export_import_catalogus_with_relations(self):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]

        response = form.submit("_export").follow()

        catalogus.delete()
        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        with open(self.filename, "rb") as f:
            form["file"] = (
                self.filename,
                f.read(),
            )
            response = form.submit("_import")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakInformatieobjectType.objects.get()
        roltype = RolType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_import_catalogus_already_exists(self):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]

        response = form.submit("_export").follow()

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        with open(self.filename, "rb") as f:
            form["file"] = (
                self.filename,
                f.read(),
            )
            response = form.submit("_import")

        self.assertIn(
            "validation error occurred while deserializing a Catalogus", response.text
        )
        self.assertEqual(Catalogus.objects.count(), 1)

    def tearDown(self):
        os.remove(self.filename)
