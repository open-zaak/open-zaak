# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import io
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.cache import caches
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory, UserFactory
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.tests.utils import patch_resource_validator

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
from .test_import_export_zaaktype import MockSelectielijst


@disable_admin_mfa()
class CatalogusAdminImportExportTests(MockSelectielijst, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        self.app.set_user(self.user)

        caches["import_requests"].clear()

        self.requests_mocker.reset()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_catalogus_relations_generate_new_uuids(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype,
            informatieobjecttype=informatieobjecttype,
            statustype=statustype,
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.register_uri(
                "GET", resultaattypeomschrijving, json={"omschrijving": "init"}
            )
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                omschrijving_generiek="bla",
                brondatum_archiefprocedure_afleidingswijze="afgehandeld",
                resultaattypeomschrijving=resultaattypeomschrijving,
                selectielijstklasse=f"{self.base}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
            )

        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        catalogus_uuid = catalogus.uuid
        zaaktype_uuid = zaaktype.uuid
        informatieobjecttype_uuid = informatieobjecttype.uuid
        besluittype_uuid = besluittype.uuid
        ziot_uuid = ziot.uuid
        statustype_uuid = statustype.uuid
        roltype_uuid = roltype.uuid
        resultaattype_uuid = resultaattype.uuid
        eigenschap_uuid = eigenschap.uuid

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
        f.name = "test321.zip"
        f.seek(0)
        form["file"] = (
            "test321.zip",
            f.read(),
        )

        selectielijstklasse_body = {
            "url": "https://selectielijst.openzaak.nl/api/v1/resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
            "procesType": "https://selectielijst.openzaak.nl/api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
            "procestermijn": "nihil",
        }

        self.requests_mocker.get(
            resultaattype.resultaattypeomschrijving, json={"omschrijving": "bla"}
        )
        self.requests_mocker.get(zaaktype.selectielijst_procestype, json={"jaar": 2020})
        self.requests_mocker.get(
            resultaattype.selectielijstklasse,
            json=selectielijstklasse_body,
        )
        response = form.submit("_import")

        self.assertEqual(response.status_code, 302)

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
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2020)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)
        self.assertEqual(ziot.statustype, statustype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

        self.assertNotEqual(imported_catalogus.uuid, catalogus_uuid)
        self.assertNotEqual(zaaktype.uuid, zaaktype_uuid)
        self.assertNotEqual(informatieobjecttype.uuid, informatieobjecttype_uuid)
        self.assertNotEqual(besluittype.uuid, besluittype_uuid)
        self.assertNotEqual(ziot.uuid, ziot_uuid)
        self.assertNotEqual(resultaattype.uuid, resultaattype_uuid)
        self.assertNotEqual(roltype.uuid, roltype_uuid)
        self.assertNotEqual(statustype.uuid, statustype_uuid)
        self.assertNotEqual(eigenschap.uuid, eigenschap_uuid)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @patch(
        "openzaak.components.catalogi.admin.zaaktypen.ReferentieLijstConfig.get_solo"
    )
    def test_export_import_catalogus_relations_use_existing_uuids(
        self, mock_solo, *mocks
    ):
        mock_solo.return_value = ReferentieLijstConfig(
            default_year=2020, allowed_years=[2017, 2020], service=self.service
        )
        catalogus = CatalogusFactory.create(
            rsin="000000000", domein="TEST", naam="catalogus-export"
        )
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}procestypen/39c6323d-baae-481f-8584-799ead897c78",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, vertrouwelijkheidaanduiding="openbaar"
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        statustype = StatusTypeFactory.create(
            zaaktype=zaaktype, statustype_omschrijving="bla"
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype,
            informatieobjecttype=informatieobjecttype,
            statustype=statustype,
        )
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        with requests_mock.Mocker() as m:
            resultaattypeomschrijving = (
                "https://example.com/resultaattypeomschrijving/1"
            )
            m.register_uri(
                "GET", resultaattypeomschrijving, json={"omschrijving": "init"}
            )
            resultaattype = ResultaatTypeFactory.create(
                zaaktype=zaaktype,
                omschrijving_generiek="bla",
                brondatum_archiefprocedure_afleidingswijze="afgehandeld",
                resultaattypeomschrijving=resultaattypeomschrijving,
                selectielijstklasse=f"{self.base}resultaten/a7960a70-4ab9-46f5-a2b1-82d3a3b2d8f7",
            )

        eigenschap = EigenschapFactory.create(zaaktype=zaaktype, definitie="bla")
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        catalogus_uuid = catalogus.uuid
        zaaktype_uuid = zaaktype.uuid
        informatieobjecttype_uuid = informatieobjecttype.uuid
        besluittype_uuid = besluittype.uuid
        ziot_uuid = ziot.uuid
        statustype_uuid = statustype.uuid
        roltype_uuid = roltype.uuid
        resultaattype_uuid = resultaattype.uuid
        eigenschap_uuid = eigenschap.uuid

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]

        response = form.submit("_export")

        data = response.content

        catalogus.delete()
        url = reverse("admin:catalogi_catalogus_import")

        response = self.app.get(url)

        form = response.form
        form["generate_new_uuids"] = False
        f = io.BytesIO(data)
        f.name = "catalogus-export.zip"
        f.seek(0)
        form["file"] = (
            "catalogus-export.zip",
            f.read(),
        )

        selectielijstklasse_body = {
            "url": f"{self.base}resultaten/a7960a70-4ab9-46f5-a2b1-82d3a3b2d8f7",
            "procesType": f"{self.base}procestypen/39c6323d-baae-481f-8584-799ead897c78",
            "procestermijn": "nihil",
        }
        self.requests_mocker.reset()
        self.requests_mocker.get(
            resultaattype.resultaattypeomschrijving, json={"omschrijving": "bla"}
        )
        self.requests_mocker.get(zaaktype.selectielijst_procestype, json={"jaar": 2020})
        self.requests_mocker.get(
            resultaattype.selectielijstklasse,
            json=selectielijstklasse_body,
        )
        response = form.submit("_import")

        self.assertEqual(response.status_code, 302)

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
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2020)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)
        self.assertEqual(ziot.statustype, statustype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

        self.assertEqual(imported_catalogus.uuid, catalogus_uuid)
        self.assertEqual(zaaktype.uuid, zaaktype_uuid)
        self.assertEqual(informatieobjecttype.uuid, informatieobjecttype_uuid)
        self.assertEqual(besluittype.uuid, besluittype_uuid)
        self.assertEqual(ziot.uuid, ziot_uuid)
        self.assertEqual(resultaattype.uuid, resultaattype_uuid)
        self.assertEqual(roltype.uuid, roltype_uuid)
        self.assertEqual(statustype.uuid, statustype_uuid)
        self.assertEqual(eigenschap.uuid, eigenschap_uuid)

    def test_import_catalogus_already_exists(self, *mocks):
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
            _("A validation error occurred while deserializing a {}\n{}").format(
                "Catalogus", ""
            ),
            response.text,
        )
        self.assertEqual(Catalogus.objects.count(), 1)

    def test_export_button_not_visible_on_create_new_catalogus(self, *mocks):
        url = reverse("admin:catalogi_catalogus_add")

        response = self.app.get(url)

        export_button = response.html.find("input", {"name": "_export"})
        self.assertIsNone(export_button)


@tag("readonly-user")
@disable_admin_mfa()
class ReadOnlyUserTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user = UserFactory.create(is_staff=True)
        view_catalogus = Permission.objects.get(codename="view_catalogus")
        user.user_permissions.add(view_catalogus)

        cls.user = user

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_export_catalogus(self):
        catalogus = CatalogusFactory.create()
        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Exporteren"), html)

        # try to submit it anyway
        detail_page.form.submit("_export", status=403)

    def test_import_catalogus(self):
        url = reverse("admin:catalogi_catalogus_import")

        self.app.get(url, status=403)
