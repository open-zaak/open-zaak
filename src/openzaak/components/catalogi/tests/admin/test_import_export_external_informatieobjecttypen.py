# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import io
import uuid

from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.documenten.tests.utils import (
    get_informatieobjecttype_response,
)
from openzaak.tests.utils import mock_drc_oas_get, patch_resource_validator

from ...models import (
    BesluitType,
    BesluitTypeInformatieObjectType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from .test_import_export_zaaktype import MockSelectielijst

BASE = "https://external.documenten.nl/api/v1/"
CATALOGUS = f"{BASE}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"


@tag("external-urls")
@disable_admin_mfa()
@override_settings(SITE_DOMAIN="testserver", ALLOWED_HOSTS=["testserver"])
class ExternalInformatieObjectTypeAdminImportExportTests(MockSelectielijst, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=BASE,
            label="external documenten",
            auth_type=AuthTypes.no_auth,
        )

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

        self.external = f"{BASE}informatieobjecttypen/{uuid.uuid4()}"
        self.catalogus = CatalogusFactory.create(rsin="000000000", domein="TEST")
        self.zaaktype = ZaakTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktype_omschrijving="bla",
            selectielijst_procestype=f"{self.base}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d",
        )
        self.informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            vertrouwelijkheidaanduiding="openbaar",
            zaaktypen=[],
        )
        self.besluittype = BesluitTypeFactory.create(
            catalogus=self.catalogus, informatieobjecttypen=[]
        )
        self.besluittype.zaaktypen.all().delete()
        self.besluittype.zaaktypen.set([self.zaaktype])
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=self.besluittype, informatieobjecttype=self.informatieobjecttype
        )
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=self.besluittype, informatieobjecttype=self.external
        )
        ZaakTypeInformatieObjectType.objects.create(
            zaaktype=self.zaaktype,
            informatieobjecttype=self.informatieobjecttype,
            volgnummer=1,
            richting="inkomend",
        )
        ZaakTypeInformatieObjectType.objects.create(
            zaaktype=self.zaaktype,
            informatieobjecttype=self.external,
            volgnummer=2,
            richting="uitgaand",
        )

        mock_drc_oas_get(self.requests_mocker)
        self.requests_mocker.get(
            self.external,
            json=get_informatieobjecttype_response(CATALOGUS, self.external),
        )

    @patch_resource_validator
    def test_export_import_zaaktype_with_external_informatieobjecttype(self, *mocks):
        response = self.app.get(
            reverse("admin:catalogi_zaaktype_change", args=(self.zaaktype.pk,))
        )
        data = response.forms["zaaktype_form"].submit("_export").content

        self.zaaktype.delete()
        self.informatieobjecttype.delete()
        self.besluittype.delete()

        response = self.app.get(
            reverse(
                "admin:catalogi_catalogus_import_zaaktype", args=(self.catalogus.pk,)
            )
        )
        form = response.forms[1]
        form["file"] = ("test.zip", io.BytesIO(data).read())
        form["generate_new_uuids"] = True

        response = form.submit("_import_zaaktype").follow()
        response = response.forms[1].submit("_select")

        self.assertEqual(response.status_code, 302)

        besluittype = BesluitType.objects.get()
        relations = besluittype.besluittypeinformatieobjecttype_set.order_by("pk")
        self.assertEqual(relations.count(), 2)
        self.assertIsNotNone(relations[0]._informatieobjecttype)
        self.assertEqual(relations[1]._iotype_url, self.external)

        zaaktype = ZaakType.objects.get()
        ziots = zaaktype.zaaktypeinformatieobjecttype_set.order_by("volgnummer")
        self.assertEqual(ziots.count(), 2)
        self.assertIsNotNone(ziots[0]._informatieobjecttype)
        self.assertEqual(ziots[1]._iotype_url, self.external)
