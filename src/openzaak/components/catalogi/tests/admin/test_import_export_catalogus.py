import io
import os
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import ugettext as _

import requests_mock
from django_webtest import WebTest
from zds_client.tests.mocks import mock_client

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import (
    BesluitType,
    Catalogus,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


class CatalogusAdminImportExportTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)
        self.filename = os.path.join(
            settings.PRIVATE_MEDIA_ROOT, "uploads/imports/TEST.zip"
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_export_import_catalogus_with_relations(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype="https://example.com/",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            omschrijving_generiek="bla",
            brondatum_archiefprocedure_afleidingswijze="ander_datumkenmerk",
            brondatum_archiefprocedure_datumkenmerk="datum",
            brondatum_archiefprocedure_registratie="bla",
            brondatum_archiefprocedure_objecttype="besluit",
        )

        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]

        response = form.submit("_export")

        data = response.content

        catalogus.delete()
        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        responses = {
            resultaattype.resultaattypeomschrijving: {
                "url": resultaattype.resultaattypeomschrijving,
                "omschrijving": "bla",
                "definitie": "bla",
                "opmerking": "adasdasd",
            },
            resultaattype.selectielijstklasse: {
                "url": resultaattype.selectielijstklasse,
                "procesType": zaaktype.selectielijst_procestype,
                "nummer": 1,
                "naam": "bla",
                "herkomst": "adsad",
                "waardering": "blijvend_bewaren",
                "procestermijn": "P5Y",
            },
        }

        with requests_mock.Mocker() as m:
            m.get(resultaattype.resultaattypeomschrijving, json={"omschrijving": "bla"})
            with mock_client(responses):
                response = form.submit("_import")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
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
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_import_catalogus_already_exists(self):
        catalogus = CatalogusFactory.create(
            rsin="000000000",
            domein="TEST",
            contactpersoon_beheer_naam="bla",
            contactpersoon_beheer_telefoonnummer="0612345678",
            contactpersoon_beheer_emailadres="test@test.nl",
        )

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]

        response = form.submit("_export")

        data = response.content

        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        response = form.submit("_import")

        self.assertIn(
            _("A validation error occurred while deserializing a Catalogus"),
            response.text,
        )
        self.assertEqual(Catalogus.objects.count(), 1)
