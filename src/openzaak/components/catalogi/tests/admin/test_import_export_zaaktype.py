# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import io
import zipfile
from datetime import datetime
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core.management import CommandError
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from django_webtest import TransactionWebTest, WebTest
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.accounts.tests.factories import SuperUserFactory, UserFactory
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_resource_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
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


class MockSelectielijst(SelectieLijstMixin):
    def setUp(self):
        # Duplicated from the original mixin, because the Transaction tests do not run
        # `setUpTestData`
        self.base = "https://selectielijst.openzaak.nl/api/v1/"
        service, _ = Service.objects.update_or_create(
            api_root=self.base,
            defaults=dict(
                slug=self.base,
                api_type=APITypes.orc,
                label="external selectielijst",
                auth_type=AuthTypes.no_auth,
            ),
        )

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.default_year = 2020
        config.allowed_years = [2017, 2020]
        config.service = service
        config.save()

        super().setUp()

        self.procestype = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_resource_get(
            self.requests_mocker,
            "procestypen",
            self.procestype,
        )

        self.selectielijstklasse = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        mock_resource_get(
            self.requests_mocker,
            "resultaten",
            self.selectielijstklasse,
        )

        self.resultaattypeomschrijving = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )
        mock_resource_get(
            self.requests_mocker,
            "resultaattypeomschrijvingen",
            self.resultaattypeomschrijving,
        )


@disable_admin_mfa()
class ZaakTypeAdminImportExportTests(MockSelectielijst, WebTest):
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

        self.catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        self.zaaktype = ZaakTypeFactory.create(
            uuid="3d7107cb-b8c2-4573-bd7e-8f2e51f7df4a",
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )
        self.informatieobjecttype = InformatieObjectTypeFactory.create(
            uuid="1f93ace1-eddc-4ece-b2e4-b53fd3f4321f",
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktypen=[],
        )
        self.besluittype = BesluitTypeFactory.create(
            uuid="53634679-9cea-4219-921e-9cc46d3f42f0", catalogus=self.catalogus
        )
        self.besluittype.zaaktypen.all().delete()
        self.besluittype.zaaktypen.set([self.zaaktype])
        self.besluittype.informatieobjecttypen.set([self.informatieobjecttype])
        self.ziot = ZaakTypeInformatieObjectTypeFactory.create(
            uuid="6a500e97-3e1e-4cae-983b-f8d6899271de",
            zaaktype=self.zaaktype,
            informatieobjecttype=self.informatieobjecttype,
        )
        self.statustype = StatusTypeFactory.create(
            uuid="ec6d4afd-e57a-424c-ab73-7abd367dc1c8",
            zaaktype=self.zaaktype,
            statustype_omschrijving="bla",
        )
        self.roltype = RolTypeFactory.create(
            uuid="664f289b-f4a8-4b23-9dae-1c5deac0380b", zaaktype=self.zaaktype
        )
        self.resultaattype = ResultaatTypeFactory.create(
            uuid="2ce77096-6ffd-481d-bbc7-d591315e5be0",
            zaaktype=self.zaaktype,
            omschrijving_generiek="bla",
            brondatum_archiefprocedure_afleidingswijze="afgehandeld",
            resultaattypeomschrijving=self.resultaattypeomschrijving,
            selectielijstklasse=self.selectielijstklasse,
        )
        self.eigenschap = EigenschapFactory.create(
            uuid="9f71f141-573e-4499-812a-df552d1c58a1",
            zaaktype=self.zaaktype,
            definitie="bla",
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_with_relations_keep_uuids(self, *mocks):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()
        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = False

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertEqual(besluittype.uuid, UUID("53634679-9cea-4219-921e-9cc46d3f42f0"))
        self.assertEqual(besluittype.catalogus, self.catalogus)
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(
            informatieobjecttype.uuid, UUID("1f93ace1-eddc-4ece-b2e4-b53fd3f4321f")
        )
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertEqual(zaaktype.uuid, UUID("3d7107cb-b8c2-4573-bd7e-8f2e51f7df4a"))
        self.assertEqual(zaaktype.catalogus, self.catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2017)
        self.assertTrue(zaaktype.concept)

        self.assertEqual(ziot.uuid, UUID("6a500e97-3e1e-4cae-983b-f8d6899271de"))
        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.uuid, UUID("664f289b-f4a8-4b23-9dae-1c5deac0380b"))
        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.uuid, UUID("2ce77096-6ffd-481d-bbc7-d591315e5be0")
        )
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.uuid, UUID("ec6d4afd-e57a-424c-ab73-7abd367dc1c8"))
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.uuid, UUID("9f71f141-573e-4499-812a-df552d1c58a1"))
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_with_relations_generate_new_uuids(self, *mocks):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()
        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = True

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertNotEqual(
            besluittype.uuid, UUID("53634679-9cea-4219-921e-9cc46d3f42f0")
        )
        self.assertEqual(besluittype.catalogus, self.catalogus)
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertNotEqual(
            informatieobjecttype.uuid, UUID("1f93ace1-eddc-4ece-b2e4-b53fd3f4321f")
        )
        self.assertEqual(informatieobjecttype.catalogus, self.catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertNotEqual(zaaktype.uuid, UUID("3d7107cb-b8c2-4573-bd7e-8f2e51f7df4a"))
        self.assertEqual(zaaktype.catalogus, self.catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2017)
        self.assertTrue(zaaktype.concept)

        self.assertNotEqual(ziot.uuid, UUID("6a500e97-3e1e-4cae-983b-f8d6899271de"))
        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertNotEqual(roltype.uuid, UUID("664f289b-f4a8-4b23-9dae-1c5deac0380b"))
        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertNotEqual(
            resultaattype.uuid, UUID("2ce77096-6ffd-481d-bbc7-d591315e5be0")
        )
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertNotEqual(
            statustype.uuid, UUID("ec6d4afd-e57a-424c-ab73-7abd367dc1c8")
        )
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertNotEqual(
            eigenschap.uuid, UUID("9f71f141-573e-4499-812a-df552d1c58a1")
        )
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_to_different_catalogus_keep_uuids(self, *mocks):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.catalogus.delete()

        catalogus = CatalogusFactory.create(rsin="015006864", domein="TEST2")
        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = False

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

        existing_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertEqual(existing_catalogus.domein, "TEST2")

        self.assertEqual(besluittype.uuid, UUID("53634679-9cea-4219-921e-9cc46d3f42f0"))
        self.assertEqual(besluittype.catalogus, existing_catalogus)
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(
            informatieobjecttype.uuid, UUID("1f93ace1-eddc-4ece-b2e4-b53fd3f4321f")
        )
        self.assertEqual(informatieobjecttype.catalogus, existing_catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertEqual(zaaktype.uuid, UUID("3d7107cb-b8c2-4573-bd7e-8f2e51f7df4a"))
        self.assertEqual(zaaktype.catalogus, existing_catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2017)
        self.assertTrue(zaaktype.concept)

        self.assertEqual(ziot.uuid, UUID("6a500e97-3e1e-4cae-983b-f8d6899271de"))
        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.uuid, UUID("664f289b-f4a8-4b23-9dae-1c5deac0380b"))
        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.uuid, UUID("2ce77096-6ffd-481d-bbc7-d591315e5be0")
        )
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.uuid, UUID("ec6d4afd-e57a-424c-ab73-7abd367dc1c8"))
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.uuid, UUID("9f71f141-573e-4499-812a-df552d1c58a1"))
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_to_different_catalogus_generate_new_uuids(
        self, *mocks
    ):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.catalogus.delete()

        catalogus = CatalogusFactory.create(rsin="015006864", domein="TEST2")
        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = True

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

        existing_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()
        roltype = RolType.objects.get()
        resultaattype = ResultaatType.objects.get()
        statustype = StatusType.objects.get()
        eigenschap = Eigenschap.objects.get()

        self.assertEqual(existing_catalogus.domein, "TEST2")

        self.assertNotEqual(
            besluittype.uuid, UUID("53634679-9cea-4219-921e-9cc46d3f42f0")
        )
        self.assertEqual(besluittype.catalogus, existing_catalogus)
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertNotEqual(
            informatieobjecttype.uuid, UUID("1f93ace1-eddc-4ece-b2e4-b53fd3f4321f")
        )
        self.assertEqual(informatieobjecttype.catalogus, existing_catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertNotEqual(zaaktype.uuid, UUID("3d7107cb-b8c2-4573-bd7e-8f2e51f7df4a"))
        self.assertEqual(zaaktype.catalogus, existing_catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2017)
        self.assertTrue(zaaktype.concept)

        self.assertNotEqual(ziot.uuid, UUID("6a500e97-3e1e-4cae-983b-f8d6899271de"))
        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertNotEqual(roltype.uuid, UUID("664f289b-f4a8-4b23-9dae-1c5deac0380b"))
        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertNotEqual(
            resultaattype.uuid, UUID("2ce77096-6ffd-481d-bbc7-d591315e5be0")
        )
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertNotEqual(
            statustype.uuid, UUID("ec6d4afd-e57a-424c-ab73-7abd367dc1c8")
        )
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertNotEqual(
            eigenschap.uuid, UUID("9f71f141-573e-4499-812a-df552d1c58a1")
        )
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_export_import_zaaktype_choose_existing_informatieobjecttype(self, *mocks):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.zaaktype.delete()
        self.besluittype.delete()

        self.informatieobjecttype.omschrijving = "existing"
        self.informatieobjecttype.save()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()

        response.form["iotype-0-existing"] = self.informatieobjecttype.id
        response = response.form.submit("_select")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)
        self.assertEqual(informatieobjecttype.omschrijving, "existing")
        self.assertEqual(
            informatieobjecttype.uuid, UUID("1f93ace1-eddc-4ece-b2e4-b53fd3f4321f")
        )

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_export_import_zaaktype_choose_existing_besluittype(self, *mocks):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.zaaktype.delete()
        self.informatieobjecttype.delete()

        self.besluittype.omschrijving = "existing"
        self.besluittype.save()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()

        response.form["besluittype-0-existing"] = self.besluittype.id
        response = response.form.submit("_select")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(besluittype.omschrijving, "existing")
        self.assertEqual(besluittype.uuid, UUID("53634679-9cea-4219-921e-9cc46d3f42f0"))
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_export_import_zaaktype_choose_existing_besluittype_and_informatieobjecttype(
        self, *mocks
    ):
        url = reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        self.zaaktype.refresh_from_db()
        self.zaaktype.delete()

        self.informatieobjecttype.omschrijving = "existing"
        self.informatieobjecttype.save()
        self.besluittype.omschrijving = "existing"
        self.besluittype.save()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()

        response.form["besluittype-0-existing"] = self.besluittype.id
        response.form["iotype-0-existing"] = self.informatieobjecttype.id
        response = response.form.submit("_select")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(besluittype.omschrijving, "existing")
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)
        self.assertEqual(informatieobjecttype.omschrijving, "existing")

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_simultaneous_zaaktype_imports(self, *mocks):
        # catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype1 = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="geheim",
            zaaktype_omschrijving="zaaktype1",
        )
        zaaktype2 = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="zaaktype2",
        )
        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="1"
        )
        besluittype1.zaaktypen.set([zaaktype1])

        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="2"
        )
        besluittype2.zaaktypen.set([zaaktype2])

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype1.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data_zaaktype1 = response.content

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype2.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data_zaaktype2 = response.content

        ZaakType.objects.all().delete()
        BesluitType.objects.all().delete()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        self.app2 = self.app_class()

        user2 = SuperUserFactory.create()
        self.app2.set_user(user2)

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data_zaaktype1)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()

        response2 = self.app2.get(url)

        form = response2.form
        f = io.BytesIO(data_zaaktype2)
        f.name = "test2.zip"
        f.seek(0)
        form["file"] = (
            "test2.zip",
            f.read(),
        )

        response2 = form.submit("_import_zaaktype").follow()

        response = response.form.submit("_select")

        Catalogus.objects.get()
        zaaktype = ZaakType.objects.get()

        self.assertEqual(zaaktype.zaaktype_omschrijving, "zaaktype1")

        response2 = response2.form.submit("_select")

        self.assertEqual(ZaakType.objects.count(), 2)
        zaaktype1, zaaktype2 = ZaakType.objects.all().order_by("zaaktype_omschrijving")

        self.assertEqual(zaaktype1.zaaktype_omschrijving, "zaaktype1")
        self.assertEqual(zaaktype2.zaaktype_omschrijving, "zaaktype2")

        self.assertEqual(BesluitType.objects.count(), 2)
        besluittype1, besluittype2 = BesluitType.objects.all().order_by("pk")

        self.assertEqual(besluittype1.omschrijving, "1")
        self.assertEqual(besluittype2.omschrijving, "2")

    def test_import_button_not_visible_on_create_new_catalogus(self, *mocks):
        url = reverse("admin:catalogi_catalogus_add")

        response = self.app.get(url)

        import_button = response.html.find("input", {"name": "_import_zaaktype"})
        self.assertIsNone(import_button)

    def test_export_published_zaaktype(self, *mocks):
        """
        Regression test for #964 - export published zaaktype.
        """
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            concept=False,
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        self.assertEqual(response.status_code, 200)

    def test_import_zaaktype_besluittype_and_informatieobjecttype_order(self, *mocks):
        self.informatieobjecttype.delete()
        self.besluittype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )

        iot_1 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Brave",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )
        iot_3 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_4 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-17",
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype3 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Banana",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype4 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Banana",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-17",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        response = form.submit("_import_zaaktype").follow()

        iotype_field_0 = response.form["iotype-0-existing"]
        self.assertEqual(len(iotype_field_0.options), 5)
        # Create new object
        self.assertEqual(iotype_field_0.options[0][2], _("Create new"))
        # First alphabetically, first date wise
        self.assertEqual(iotype_field_0.options[1][0], str(iot_3.id))
        self.assertEqual(iotype_field_0.options[1][2], str(iot_3))
        # First alphabetically, second date wise
        self.assertEqual(iotype_field_0.options[2][0], str(iot_2.id))
        self.assertEqual(iotype_field_0.options[2][2], str(iot_2))
        # Second alphabetically, First date wise
        self.assertEqual(iotype_field_0.options[3][0], str(iot_1.id))
        self.assertEqual(iotype_field_0.options[3][2], str(iot_1))
        # Second alphabetically, second date wise
        self.assertEqual(iotype_field_0.options[4][0], str(iot_4.id))
        self.assertEqual(iotype_field_0.options[4][2], str(iot_4))

        # BesluitType exists and should be selected
        besluittype_field_0 = response.form["besluittype-0-existing"]
        self.assertEqual(len(besluittype_field_0.options), 5)
        # Create new object
        self.assertEqual(besluittype_field_0.options[0][2], _("Create new"))
        # First alphabetically, first date wise
        self.assertEqual(besluittype_field_0.options[1][0], str(besluittype1.id))
        self.assertEqual(besluittype_field_0.options[1][2], str(besluittype1))
        # First alphabetically, second date wise
        self.assertEqual(besluittype_field_0.options[2][0], str(besluittype2.id))
        self.assertEqual(besluittype_field_0.options[2][2], str(besluittype2))
        # Second alphabetically, First date wise
        self.assertEqual(besluittype_field_0.options[3][0], str(besluittype4.id))
        self.assertEqual(besluittype_field_0.options[3][2], str(besluittype4))
        # Second alphabetically, second date wise
        self.assertEqual(besluittype_field_0.options[4][0], str(besluittype3.id))
        self.assertEqual(besluittype_field_0.options[4][2], str(besluittype3))

    def test_import_zaaktype_besluittype_and_informatieobjecttype_field_order(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        iot_1 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )
        iot_3 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_4 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-17",
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype3 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Banana",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype4 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Banana",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-17",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        response = form.submit("_import_zaaktype").follow()
        returned_labels = [str(label) for label in response.html.find_all("label")]

        expected_labels = [
            f'<label for="id_iotype-0-existing">{self.catalogus} - {iot_3.omschrijving}:</label>',
            f'<label for="id_iotype-1-existing">{self.catalogus} - {iot_2.omschrijving}:</label>',
            f'<label for="id_iotype-2-existing">{self.catalogus} - {iot_1.omschrijving}:</label>',
            f'<label for="id_iotype-3-existing">{self.catalogus} - {iot_4.omschrijving}:</label>',
            f'<label for="id_besluittype-0-existing">{self.catalogus} - {besluittype1.omschrijving}:</label>',
            f'<label for="id_besluittype-1-existing">{self.catalogus} - {besluittype2.omschrijving}:</label>',
            f'<label for="id_besluittype-2-existing">{self.catalogus} - {besluittype4.omschrijving}:</label>',
            f'<label for="id_besluittype-3-existing">{self.catalogus} - {besluittype3.omschrijving}:</label>',
        ]

        self.assertEqual(returned_labels, expected_labels)

        with patch(
            "openzaak.components.catalogi.admin.admin_views.construct_iotypen",
            side_effect=CommandError("some error"),
        ):
            response = response.form.submit("_select")
        self.assertEqual(response.status_code, 200)
        # labels should be correct on form validation failure
        self.assertEqual(returned_labels, expected_labels)

    def test_import_zaaktype_saved_selected_on_error(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        Catalogus.objects.exclude(pk=self.catalogus.pk)
        iot_1 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )
        iot_2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
        )
        iot_3 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Charlie",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="Apple", zaaktypen=[zaaktype]
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="Banana", zaaktypen=[zaaktype]
        )
        besluittype3 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="Banana", zaaktypen=[zaaktype]
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        response = form.submit("_import_zaaktype").follow()
        # default value and order of fields is not guaranteed, will be in #1493
        response.form["iotype-0-existing"].value = iot_3.pk
        response.form["iotype-1-existing"].value = iot_1.pk
        response.form["iotype-2-existing"].value = iot_2.pk

        response.form["besluittype-0-existing"].value = besluittype3.pk
        response.form["besluittype-1-existing"].value = besluittype1.pk
        response.form["besluittype-2-existing"].value = besluittype2.pk

        with patch(
            "openzaak.components.catalogi.admin.admin_views.construct_iotypen",
            side_effect=CommandError("some error"),
        ):
            response = response.form.submit("_select")

        # should fail as it imports overlapping IOTs and besluit types
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.form["iotype-0-existing"].value, str(iot_3.pk))
        self.assertEqual(response.form["iotype-1-existing"].value, str(iot_1.pk))
        self.assertEqual(response.form["iotype-2-existing"].value, str(iot_2.pk))

        self.assertEqual(
            response.form["besluittype-0-existing"].value, str(besluittype3.pk)
        )
        self.assertEqual(
            response.form["besluittype-1-existing"].value, str(besluittype1.pk)
        )
        self.assertEqual(
            response.form["besluittype-2-existing"].value, str(besluittype2.pk)
        )

    def test_import_zaaktype_auto_match_besluittype_and_informatieobjecttype(
        self, *mocks
    ):
        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )
        informatieobjecttype2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Beta",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="1"
        )
        besluittype1.zaaktypen.set([zaaktype])

        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="2"
        )
        besluittype2.zaaktypen.set([zaaktype])

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        # one should be new
        informatieobjecttype2.delete()
        besluittype2.delete()

        response = form.submit("_import_zaaktype").follow()

        # IOT exists and should be selected
        iotype_field_0 = response.form["iotype-0-existing"]
        self.assertEqual(len(iotype_field_0.options), 2)
        self.assertEqual(  # default option not selected
            iotype_field_0.options[0], ("", False, _("Create new"))
        )
        self.assertEqual(  # option 1 is selected
            iotype_field_0.options[1],
            (str(informatieobjecttype.pk), True, str(informatieobjecttype)),
        )
        self.assertEqual(iotype_field_0.value, str(informatieobjecttype.pk))

        # IOT does not exist and should select create new
        iotype_field_1 = response.form["iotype-1-existing"]
        self.assertEqual(len(iotype_field_1.options), 2)
        self.assertEqual(  # default option selected
            iotype_field_1.options[0], ("", True, _("Create new"))
        )
        self.assertEqual(  # option 1 not selected
            iotype_field_1.options[1],
            (str(informatieobjecttype.pk), False, str(informatieobjecttype)),
        )
        self.assertEqual(iotype_field_1.value, "")

        # BesluitType exists and should be selected
        besluittype_field_0 = response.form["besluittype-0-existing"]
        self.assertEqual(len(besluittype_field_0.options), 2)
        self.assertEqual(  # default option not selected
            besluittype_field_0.options[0], ("", False, _("Create new"))
        )
        self.assertEqual(  # option 1 is selected
            besluittype_field_0.options[1],
            (str(besluittype1.pk), True, str(besluittype1)),
        )
        self.assertEqual(besluittype_field_0.value, str(besluittype1.pk))

        # BesluitType does not exist and should select create new
        besluittype_field_1 = response.form["besluittype-1-existing"]
        self.assertEqual(len(besluittype_field_1.options), 2)
        self.assertEqual(  # default option selected
            besluittype_field_1.options[0], ("", True, _("Create new"))
        )
        self.assertEqual(  # option 1 not selected
            besluittype_field_1.options[1],
            (str(besluittype1.pk), False, str(besluittype1)),
        )
        self.assertEqual(besluittype_field_1.value, "")

    def test_import_zaaktype_auto_match_import_relations(self, *mocks):
        self.zaaktype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )

        informatieobjecttype2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Beta",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="Apple", zaaktypen=[zaaktype]
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus, omschrijving="Charlie", zaaktypen=[zaaktype]
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        zaaktype.delete()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        # one should be new
        informatieobjecttype2.delete()
        besluittype2.delete()

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.all().count(), 1)

        new_zaaktype = ZaakType.objects.get()

        old_iot = new_zaaktype.informatieobjecttypen.all().get(omschrijving="Alpha")
        self.assertEqual(old_iot, informatieobjecttype)
        new_iot = new_zaaktype.informatieobjecttypen.all().get(omschrijving="Beta")
        self.assertNotEqual(new_iot.pk, informatieobjecttype2.pk)

        old_besluittype = new_zaaktype.besluittypen.all().get(omschrijving="Apple")
        self.assertEqual(old_besluittype, besluittype1)
        new_besluittype = new_zaaktype.besluittypen.all().get(omschrijving="Charlie")
        self.assertNotEqual(new_besluittype.pk, besluittype2.pk)

    def test_import_zaaktype_auto_match_latest_object(self, *mocks):
        self.zaaktype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        iot1 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        # New types not found in zip
        iot2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-04-01",
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-04-01",
        )

        zaaktype.delete()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()

        iotype_field = response.form["iotype-0-existing"]
        self.assertNotEqual(iotype_field.value, str(iot1.pk))
        self.assertEqual(iotype_field.value, str(iot2.pk))

        bt_field = response.form["besluittype-0-existing"]
        self.assertNotEqual(bt_field.value, str(besluittype1.pk))
        self.assertEqual(bt_field.value, str(besluittype2.pk))

        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

        new_zaaktype = ZaakType.objects.exclude(pk=zaaktype.pk).get()
        old_iot = new_zaaktype.informatieobjecttypen.get()
        self.assertEqual(old_iot, iot2)

        old_bt = new_zaaktype.besluittypen.get()
        self.assertEqual(old_bt, besluittype2)

    def test_import_iotype_without_omschrijving_generiek(self, *mocks):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1509
        """
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving_generiek_informatieobjecttype="",
            omschrijving_generiek_definitie="",
            omschrijving_generiek_herkomst="",
            omschrijving_generiek_hierarchie="",
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        # export
        zaaktype_url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(zaaktype_url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        export_data = response.content

        zaaktype.delete()
        informatieobjecttype.delete()

        # import to the new catalogus
        import_url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(import_url)

        form = response.form
        f = io.BytesIO(export_data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)

    def test_import_zaaktype_with_no_identification_selected(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie="ZAAKTYPE_1",
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["identificatie_prefix"] = ""

        zaaktype.delete()
        self.assertFalse(ZaakType.objects.filter(identificatie="ZAAKTYPE_1").exists())

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ZaakType.objects.filter(identificatie="ZAAKTYPE_1").exists())

    def test_import_zaaktype_with_different_identification(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie="ZAAKTYPE_1",
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        zaaktype.delete()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["identificatie_prefix"] = "PREFIX"
        response = form.submit("_import_zaaktype").follow()

        response = response.form.submit("_select")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.all().count(), 2)
        self.assertTrue(
            ZaakType.objects.filter(identificatie="PREFIX_ZAAKTYPE_1").exists()
        )

    def test_import_zaaktype_with_different_identification_exceeds_max_length(
        self, *mocks
    ):
        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            identificatie="Identification_that_is_fifty_characters_long_00000",
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        form["identificatie_prefix"] = "PREFIX"
        response = form.submit("_import_zaaktype").follow()

        response = response.form.submit("_select")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ZaakType.objects.all().count(), 1)

        self.assertIn(
            _("Identification {} is too long with prefix. Max 50 characters.").format(
                "PREFIX_" + "Identification_that_is_fifty_characters_long_00000"
            ),
            response.text,
        )

    def test_import_zaaktype_with_bad_filenames(self, *mocks):
        ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO()
        f.name = "test.zip"
        f.seek(0)

        # files are not read, content does not matter
        with zipfile.ZipFile(f, "w") as zip_file:
            # zip_file.mkdir("some_dir")
            zip_file.writestr("some_dir/ZaakType.json", '{"placeholder": "data"}')
            zip_file.writestr(
                "some_dir/ZaakTypeInformatieObjectType.json", '{"placeholder": "data"}'
            )
            zip_file.writestr("some_dir/ResultaatType.json", '{"placeholder": "data"}')
            zip_file.writestr("some_dir/RolType.json", '{"placeholder": "data"}')
            zip_file.writestr("some_dir/StatusType.json", '{"placeholder": "data"}')
            zip_file.writestr("some_dir/Eigenschap.json", '{"placeholder": "data"}')

        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype")
        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])

        msg = _(
            "No files found. Expected: {files_not_found} but received:<br> {files_received}"
        )
        files_not_found = (
            "ZaakType.json, ZaakTypeInformatieObjectType.json, ResultaatType.json, RolType.json, "
            "StatusType.json, Eigenschap.json"
        )
        files_received = (
            "some_dir/ZaakType.json, some_dir/ZaakTypeInformatieObjectType.json, some_dir/ResultaatType.json, "
            "some_dir/RolType.json, some_dir/StatusType.json, some_dir/Eigenschap.json"
        )

        self.assertEqual(
            str(messages[0]),
            format_html(
                msg, files_not_found=files_not_found, files_received=files_received
            ),
        )

    def test_import_zaaktype_with_bad_filenames_with_correct_besluittype_and_informatieobjecttype(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )
        BesluitTypeFactory.create(
            catalogus=self.catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )

        response = self.app.get(url)

        form = response.form
        fin = io.BytesIO(data)
        fin.name = "test.zip"
        fin.seek(0)

        fout = io.BytesIO()
        fout.name = "test.zip"
        fout.seek(0)

        # create zip with bad structure
        with zipfile.ZipFile(fin, "r") as zin:
            with zipfile.ZipFile(fout, "w") as zout:
                for zipInfo in zin.infolist():
                    buffer = zin.read(zipInfo.filename)
                    if zipInfo.filename not in [
                        "InformatieObjectType.json",
                        "BesluitType.json",
                    ]:
                        zipInfo.filename = "some_dir/" + zipInfo.filename
                    zout.writestr(zipInfo, buffer)
        fout.seek(0)
        form["file"] = (
            "test.zip",
            fout.read(),
        )

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])

        msg = _(
            "No files found. Expected: {files_not_found} but received:<br> {files_received}"
        )
        files_not_found = (
            "ZaakType.json, ZaakTypeInformatieObjectType.json, ResultaatType.json, RolType.json, "
            "StatusType.json, Eigenschap.json"
        )
        files_received = (
            "some_dir/ZaakType.json, BesluitType.json, InformatieObjectType.json, "
            "some_dir/ZaakTypeInformatieObjectType.json"
        )
        self.assertEqual(
            str(messages[0]),
            format_html(
                msg, files_not_found=files_not_found, files_received=files_received
            ),
        )

    def test_export_import_zaaktype_maintains_iot_volgnummer(self, *mocks):
        """
        Regression test that imported volgnummer is the same as in the export
        """
        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()

        zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=self.procestype,
        )

        informatieobjecttype_1 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktypen=None,
            omschrijving="Apple",
        )
        ziot_1a = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_1, volgnummer=1
        )
        informatieobjecttype_2 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktypen=None,
            omschrijving="Banana",
        )
        ziot_2a = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_2, volgnummer=2
        )
        ziot_1b = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_1, volgnummer=3
        )
        ziot_2b = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_2, volgnummer=4
        )
        informatieobjecttype_3 = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktypen=None,
            omschrijving="Chair",
        )
        ziot_3a = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_3, volgnummer=5
        )
        ziot_2c = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype_2, volgnummer=6
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        zaaktype.delete()
        informatieobjecttype_1.delete()
        informatieobjecttype_2.delete()
        informatieobjecttype_3.delete()

        url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
        )
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        response = form.submit("_import_zaaktype").follow()
        response.form.submit("_select")

        self.assertEqual(ZaakType.objects.filter(catalogus=self.catalogus).count(), 1)
        new_zaaktype = ZaakType.objects.get(catalogus=self.catalogus)
        self.assertEqual(
            InformatieObjectType.objects.filter(catalogus=self.catalogus).count(), 3
        )
        self.assertEqual(
            ZaakTypeInformatieObjectType.objects.filter(zaaktype=new_zaaktype).count(),
            6,
        )
        # verify ZaakTypeInformatieObjectType are imported correctly
        new_iot_1 = InformatieObjectType.objects.get(
            catalogus=self.catalogus, omschrijving="Apple"
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_1,
                volgnummer=ziot_1a.volgnummer,
            ).exists()
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_1,
                volgnummer=ziot_1b.volgnummer,
            ).exists()
        )

        new_iot_2 = InformatieObjectType.objects.get(
            catalogus=self.catalogus, omschrijving="Banana"
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_2,
                volgnummer=ziot_2a.volgnummer,
            ).exists()
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_2,
                volgnummer=ziot_2b.volgnummer,
            ).exists()
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_2,
                volgnummer=ziot_2c.volgnummer,
            ).exists()
        )

        new_iot_2 = InformatieObjectType.objects.get(
            catalogus=self.catalogus, omschrijving="Chair"
        )
        self.assertTrue(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype=new_zaaktype,
                informatieobjecttype=new_iot_2,
                volgnummer=ziot_3a.volgnummer,
            ).exists()
        )


@disable_admin_mfa()
class ZaakTypeAdminImportExportTransactionTests(MockSelectielijst, TransactionWebTest):
    def setUp(self):
        super().setUp()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        self.app.set_user(SuperUserFactory.create())

        conf = ReferentieLijstConfig.get_solo()
        conf.default_year = 2020
        conf.allowed_years = [2020]
        conf.save()

    def test_import_zaaktype_besluittype_invalid_eigenschap(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.delete()
        besluittype.delete()

        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)

        with zipfile.ZipFile(f, "a") as zip_file:
            zip_file.writestr("Eigenschap.json", '[{"incorrect": "data"}]')

        f.seek(0)

        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "Eigenschap", ""
            ),
            response.text,
        )
        self.assertEqual(BesluitType.objects.count(), 0)
        self.assertEqual(ZaakType.objects.count(), 0)
        self.assertEqual(Eigenschap.objects.count(), 0)

    def test_import_zaaktype_invalid_eigenschap(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.delete()

        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))

        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)

        with zipfile.ZipFile(f, "a") as zip_file:
            zip_file.writestr("Eigenschap.json", '[{"incorrect": "data"}]')

        f.seek(0)

        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "Eigenschap", ""
            ),
            response.text,
        )
        self.assertEqual(ZaakType.objects.count(), 0)
        self.assertEqual(Eigenschap.objects.count(), 0)

    def test_import_zaaktype_informatieobjectype_overlapping(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
        )

        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = True

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        zaaktype.save()

        response = form.submit("_import_zaaktype").follow()
        form = response.form
        form["iotype-0-existing"].value = ""
        response = form.submit("_select")

        # ensure form submits correctly
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InformatieObjectType.objects.all().count(), 2)

    def test_import_zaaktype_besluittype_overlapping(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )
        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-01-01",
        )
        # create zip
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))
        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        response = form.submit("_export")
        data = response.content

        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))
        response = self.app.get(url)

        form = response.form
        f = io.BytesIO(data)
        f.name = "test.zip"
        f.seek(0)
        form["file"] = (
            "test.zip",
            f.read(),
        )
        form["generate_new_uuids"] = True

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        zaaktype.save()

        response = form.submit("_import_zaaktype").follow()
        form = response.form
        form["besluittype-0-existing"].value = ""
        response = form.submit("_select")

        # ensure form submits correctly
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BesluitType.objects.all().count(), 2)


@tag("readonly-user")
@disable_admin_mfa()
class ReadOnlyUserTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user = UserFactory.create(is_staff=True)
        view_zaaktype = Permission.objects.get(codename="view_zaaktype")
        view_catalogus = Permission.objects.get(codename="view_catalogus")
        user.user_permissions.add(view_zaaktype, view_catalogus)

        cls.user = user

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_export_catalogus(self):
        zaaktype = ZaakTypeFactory.create()
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Exporteren"), html)

        # try to submit it anyway
        detail_page.form.submit("_export", status=403)

    def test_import_catalogus_zaaktype(self):
        catalogus = CatalogusFactory.create()
        import_url = reverse(
            "admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,)
        )
        select_url = reverse(
            "admin:catalogi_catalogus_import_zaaktype_select", args=(catalogus.pk,)
        )

        for url in (import_url, select_url):
            with self.subTest(url=url, method="get"):
                self.app.get(url, status=403)
            with self.subTest(url=url, method="post"):
                self.app.post(url, status=403)
