# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import io
import zipfile
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.translation import ugettext as _

import requests_mock
from django_webtest import TransactionWebTest, WebTest
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

mock_selectielijst_client = Service(
    label="VNG Selectielijst",
    api_type=APITypes.orc,
    api_root="https://selectielijst.openzaak.nl/api/v1/",
    oas="https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml",
    auth_type=AuthTypes.no_auth,
).build_client()


class MockSelectielijst(SelectieLijstMixin):
    def setUp(self):
        super().setUp()

        mock_resource_get(
            self.requests_mocker,
            "procestypen",
            (
                "https://selectielijst.openzaak.nl/api/v1/"
                "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
            ),
        )
        mock_resource_get(
            self.requests_mocker,
            "resultaten",
            (
                "https://selectielijst.openzaak.nl/api/v1/"
                "resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
            ),
        )


@patch(
    "openzaak.components.catalogi.models.zaaktype.Service.get_client",
    return_value=mock_selectielijst_client,
)
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

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_with_relations(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
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

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.refresh_from_db()
        zaaktype.delete()
        informatieobjecttype.delete()
        besluittype.delete()
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

        selectielijstklasse_body = {
            "url": "https://selectielijst.openzaak.nl/api/v1/resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829",
            "procesType": "https://selectielijst.openzaak.nl/api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
            "procestermijn": "nihil",
        }

        # with requests_mock.Mocker() as m:
        self.requests_mocker.get(
            resultaattype.resultaattypeomschrijving, json={"omschrijving": "bla"}
        )
        self.requests_mocker.get(zaaktype.selectielijst_procestype, json={"jaar": 2020})
        self.requests_mocker.get(
            resultaattype.selectielijstklasse, json=selectielijstklasse_body,
        )
        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

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
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2020)
        self.assertTrue(zaaktype.concept)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_export_import_zaaktype_to_different_catalogus(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}api/v1/procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
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

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.refresh_from_db()
        catalogus.delete()

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
            resultaattype.selectielijstklasse, json=selectielijstklasse_body,
        )
        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

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
        self.assertTrue(besluittype.concept)
        self.assertEqual(list(besluittype.zaaktypen.all()), [zaaktype])
        self.assertEqual(
            list(besluittype.informatieobjecttypen.all()), [informatieobjecttype]
        )

        self.assertEqual(informatieobjecttype.catalogus, imported_catalogus)
        self.assertTrue(informatieobjecttype.concept)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)
        self.assertEqual(zaaktype.selectielijst_procestype_jaar, 2020)
        self.assertTrue(zaaktype.concept)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

        self.assertEqual(roltype.zaaktype, zaaktype)
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(statustype.zaaktype, zaaktype)
        self.assertEqual(eigenschap.zaaktype, zaaktype)

    def test_export_import_zaaktype_choose_existing_informatieobjecttype(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="export",
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.refresh_from_db()
        zaaktype.delete()
        informatieobjecttype.delete()
        besluittype.delete()

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="existing",
        )
        informatieobjecttype_uuid = informatieobjecttype.uuid
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

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

        response = form.submit("_import_zaaktype").follow()

        response.form["iotype-0-existing"] = informatieobjecttype.id
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
        self.assertEqual(informatieobjecttype.uuid, informatieobjecttype_uuid)

        self.assertEqual(zaaktype.catalogus, imported_catalogus)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_export_import_zaaktype_choose_existing_besluittype(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="export",
        )
        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="export"
        )
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.refresh_from_db()
        zaaktype.delete()
        informatieobjecttype.delete()
        besluittype.delete()

        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="existing"
        )
        besluittype_uuid = besluittype.uuid
        besluittype.zaaktypen.all().delete()
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

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

        response = form.submit("_import_zaaktype").follow()

        response.form["besluittype-0-existing"] = besluittype.id
        response = response.form.submit("_select")

        imported_catalogus = Catalogus.objects.get()
        besluittype = BesluitType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        zaaktype = ZaakType.objects.get()
        ziot = ZaakTypeInformatieObjectType.objects.get()

        self.assertEqual(besluittype.catalogus, imported_catalogus)
        self.assertEqual(besluittype.omschrijving, "existing")
        self.assertEqual(besluittype.uuid, besluittype_uuid)
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
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="export",
        )
        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="export"
        )
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        besluittype.informatieobjecttypen.set([informatieobjecttype])
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.refresh_from_db()
        zaaktype.delete()
        informatieobjecttype.delete()
        besluittype.delete()

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="existing",
        )
        besluittype = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="existing"
        )
        besluittype.zaaktypen.all().delete()
        Catalogus.objects.exclude(pk=catalogus.pk).delete()

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

        response = form.submit("_import_zaaktype").follow()

        response.form["besluittype-0-existing"] = besluittype.id
        response.form["iotype-0-existing"] = informatieobjecttype.id
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

    def test_import_zaaktype_create_new_generates_new_uuids(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        zaaktype_uuid = zaaktype.uuid
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="export",
        )
        informatieobjecttype_uuid = informatieobjecttype.uuid
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        besluittype = BesluitTypeFactory.create(catalogus=catalogus)
        besluittype_uuid = besluittype.uuid
        besluittype.zaaktypen.all().delete()
        besluittype.zaaktypen.set([zaaktype])
        Catalogus.objects.exclude(pk=catalogus.pk).delete()
        ZaakType.objects.exclude(pk=zaaktype.pk).delete()

        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]

        response = form.submit("_export")

        data = response.content

        zaaktype.delete()
        informatieobjecttype.delete()
        besluittype.delete()

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

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        zaaktype = ZaakType.objects.get()
        informatieobjecttype = InformatieObjectType.objects.get()
        besluittype = BesluitType.objects.get()

        self.assertNotEqual(zaaktype.uuid, zaaktype_uuid)
        self.assertNotEqual(informatieobjecttype.uuid, informatieobjecttype_uuid)
        self.assertNotEqual(besluittype.uuid, besluittype_uuid)

    def test_simultaneous_zaaktype_imports(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype1 = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="geheim",
            zaaktype_omschrijving="zaaktype1",
        )
        zaaktype2 = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="zaaktype2",
        )
        besluittype1 = BesluitTypeFactory.create(catalogus=catalogus, omschrijving="1")
        besluittype1.zaaktypen.set([zaaktype1])

        besluittype2 = BesluitTypeFactory.create(catalogus=catalogus, omschrijving="2")
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

        url = reverse("admin:catalogi_catalogus_import_zaaktype", args=(catalogus.pk,))

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
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
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
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        Catalogus.objects.exclude(pk=catalogus.pk)
        iot_1 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Brave",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_2 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )
        iot_3 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-17",
        )
        iot_4 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-11-18",
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-17",
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype3 = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="Banana",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-11-18",
        )
        besluittype4 = BesluitTypeFactory.create(
            catalogus=catalogus,
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

    def test_import_zaaktype_saved_selected_on_error(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        Catalogus.objects.exclude(pk=catalogus.pk)
        iot_1 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )
        iot_2 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Bravo",
            zaaktypen__zaaktype=zaaktype,
        )
        iot_3 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Charlie",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="Apple", zaaktypen=[zaaktype]
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="Banana", zaaktypen=[zaaktype]
        )
        besluittype3 = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="Banana", zaaktypen=[zaaktype]
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
        response = form.submit("_import_zaaktype").follow()
        # default value and order of fields is not guaranteed, will be in #1493
        response.form["iotype-0-existing"].value = iot_3.pk
        response.form["iotype-1-existing"].value = iot_1.pk
        response.form["iotype-2-existing"].value = iot_2.pk

        response.form["besluittype-0-existing"].value = besluittype3.pk
        response.form["besluittype-1-existing"].value = besluittype1.pk
        response.form["besluittype-2-existing"].value = besluittype2.pk
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
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )
        informatieobjecttype2 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Beta",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(catalogus=catalogus, omschrijving="1")
        besluittype1.zaaktypen.set([zaaktype])

        besluittype2 = BesluitTypeFactory.create(catalogus=catalogus, omschrijving="2")
        besluittype2.zaaktypen.set([zaaktype])

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
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
        )

        informatieobjecttype2 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Beta",
            zaaktypen__zaaktype=zaaktype,
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="Apple", zaaktypen=[zaaktype]
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=catalogus, omschrijving="Charlie", zaaktypen=[zaaktype]
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

        # one should be new
        informatieobjecttype2.delete()
        besluittype2.delete()

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1)
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31)
        zaaktype.save()

        self.assertEqual(ZaakType.objects.all().count(), 1)

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ZaakType.objects.all().count(), 2)

        new_zaaktype = ZaakType.objects.exclude(pk=zaaktype.pk).get()

        old_iot = new_zaaktype.informatieobjecttypen.all().get(omschrijving="Alpha")
        self.assertEqual(old_iot, informatieobjecttype)
        new_iot = new_zaaktype.informatieobjecttypen.all().get(omschrijving="Beta")
        self.assertNotEqual(new_iot.pk, informatieobjecttype2.pk)

        old_besluittype = new_zaaktype.besluittypen.all().get(omschrijving="Apple")
        self.assertEqual(old_besluittype, besluittype1)
        new_besluittype = new_zaaktype.besluittypen.all().get(omschrijving="Charlie")
        self.assertNotEqual(new_besluittype.pk, besluittype2.pk)

    def test_import_zaaktype_auto_match_latest_object(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            datum_begin_geldigheid="2023-01-01",
        )

        iot1 = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-01-01",
            datum_einde_geldigheid="2023-03-31",
        )

        besluittype1 = BesluitTypeFactory.create(
            catalogus=catalogus,
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
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="Alpha",
            zaaktypen__zaaktype=zaaktype,
            datum_begin_geldigheid="2023-04-01",
        )
        besluittype2 = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="Apple",
            zaaktypen=[zaaktype],
            datum_begin_geldigheid="2023-04-01",
        )

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

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1)
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31)
        zaaktype.save()

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
        old_iot = new_zaaktype.informatieobjecttypen.all().get(omschrijving="Alpha")
        self.assertEqual(old_iot, iot2)

        old_bt = new_zaaktype.besluittypen.all().get(omschrijving="Apple")
        self.assertEqual(old_bt, besluittype2)


@patch(
    "openzaak.components.catalogi.models.zaaktype.Service.get_client",
    return_value=mock_selectielijst_client,
)
@override_settings(CUSTOM_CLIENT_FETCHER=None)
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

    def test_import_zaaktype_already_exists(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )

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

        response = form.submit("_import_zaaktype")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "ZaakType", ""
            ),
            response.text,
        )
        self.assertEqual(ZaakType.objects.count(), 1)

    def test_import_zaaktype_already_exists_with_besluittype(self, *mocks):
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

        besluittype.delete()

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

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "ZaakType", ""
            ),
            response.text,
        )
        self.assertEqual(ZaakType.objects.count(), 1)
        self.assertEqual(BesluitType.objects.count(), 0)

    def test_import_zaaktype_besluittype_already_exists(self, *mocks):
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

        response = form.submit("_import_zaaktype").follow()

        form = response.form
        form["besluittype-0-existing"].value = ""
        response = form.submit("_select")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "BesluitType", ""
            ),
            response.text,
        )
        self.assertEqual(BesluitType.objects.count(), 1)
        self.assertEqual(ZaakType.objects.count(), 0)

    def test_import_zaaktype_informatieobjectype_already_exists(self, *mocks):
        catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        zaaktype = ZaakTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
        )
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            omschrijving="export",
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ZaakType.objects.exclude(pk=zaaktype.pk).delete()

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
        form["file"] = (
            "test.zip",
            f.read(),
        )

        response = form.submit("_import_zaaktype").follow()
        form = response.form
        form["iotype-0-existing"].value = ""
        response = form.submit("_select")

        self.assertIn(
            _("A validation error occurred while deserializing a {}\n{}").format(
                "InformatieObjectType", ""
            ),
            response.text,
        )
        self.assertEqual(InformatieObjectType.objects.count(), 1)
        self.assertEqual(ZaakType.objects.count(), 0)

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

        informatieobjecttype = InformatieObjectTypeFactory.create(
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

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        zaaktype.save()

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 200)

        error_text = (
            _(
                "Dit {} komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
            )
            .format(informatieobjecttype._meta.verbose_name)
            .title()
        )

        expected_error = {"existing": [f"begin_geldigheid: {error_text}"]}
        iotype_forms = response.context["iotype_forms"]
        self.assertEqual(
            iotype_forms.errors, [expected_error],
        )

        informatieobjecttype.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        informatieobjecttype.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        informatieobjecttype.save()

        self.assertEqual(InformatieObjectType.objects.all().count(), 1)
        response = response.form.submit("_select")
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
        besluittype1 = BesluitTypeFactory.create(
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

        zaaktype.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        zaaktype.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        zaaktype.save()

        response = form.submit("_import_zaaktype").follow()
        response = response.form.submit("_select")

        self.assertEqual(response.status_code, 200)

        error_text = (
            _(
                "Dit {} komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
            )
            .format(besluittype1._meta.verbose_name)
            .title()
        )

        expected_error = {"existing": [f"begin_geldigheid: overlap — {error_text}"]}
        besluittype_forms = response.context["besluittype_forms"]
        self.assertEqual(
            besluittype_forms.errors, [expected_error],
        )

        besluittype1.datum_begin_geldigheid = datetime(2022, 1, 1).date()
        besluittype1.datum_einde_geldigheid = datetime(2022, 12, 31).date()
        besluittype1.save()

        self.assertEqual(BesluitType.objects.all().count(), 1)
        response = response.form.submit("_select")
        # ensure form submits correctly
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BesluitType.objects.all().count(), 2)


@tag("readonly-user")
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
