# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid as _uuid

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.components.autorisaties.models import Applicatie
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from .factories import ZaakTypeFactory


class HandleAuthNotifTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @requests_mock.Mocker()
    def test_handle_create_auth(self, m):
        zaaktype = ZaakTypeFactory.create()
        config = AuthorizationsConfig.get_solo()
        uuid = _uuid.uuid4()
        applicatie_url = (
            f"{config.authorizations_api_service.api_root}applicaties/{uuid}"
        )
        webhook_url = reverse("catalogi:notificaties-webhook")
        m.get(
            applicatie_url,
            json={
                "client_ids": ["id1"],
                "label": "Melding Openbare Ruimte consumer",
                "heeftAlleAutorisaties": False,
                "autorisaties": [
                    {
                        "component": "zrc",
                        "scopes": [
                            "zds.scopes.zaken.lezen",
                            "zds.scopes.zaken.aanmaken",
                        ],
                        "zaaktype": f"http://testserver{reverse(zaaktype)}",
                        "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    }
                ],
            },
        )
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "create",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        applicatie = Applicatie.objects.get(client_ids=["id1"])

        self.assertEqual(applicatie.uuid, uuid)

    @requests_mock.Mocker()
    def test_handle_update_auth(self, m):
        zaaktype = ZaakTypeFactory.create()
        applicatie = Applicatie.objects.create(
            client_ids=["id1"], label="before", heeft_alle_autorisaties=True
        )
        uuid = applicatie.uuid
        config = AuthorizationsConfig.get_solo()
        applicatie_url = (
            f"{config.authorizations_api_service.api_root}/applicaties/{uuid}"
        )

        self.assertEqual(applicatie.autorisaties.count(), 0)

        webhook_url = reverse("catalogi:notificaties-webhook")
        m.get(
            applicatie_url,
            json={
                "client_ids": ["id1"],
                "label": "after",
                "heeftAlleAutorisaties": False,
                "autorisaties": [
                    {
                        "component": "zrc",
                        "scopes": [
                            "zds.scopes.zaken.lezen",
                            "zds.scopes.zaken.aanmaken",
                        ],
                        "zaaktype": f"http://testserver{reverse(zaaktype)}",
                        "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    }
                ],
            },
        )
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "partial_update",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        applicatie.refresh_from_db()

        self.assertEqual(applicatie.uuid, uuid)
        self.assertEqual(applicatie.heeft_alle_autorisaties, False)
        self.assertEqual(applicatie.label, "after")

        self.assertEqual(applicatie.autorisaties.count(), 1)

    def test_handle_delete_auth(self):
        applicatie = Applicatie.objects.create(
            client_ids=["id1"], label="for delete", heeft_alle_autorisaties=True
        )
        uuid = applicatie.uuid
        config = AuthorizationsConfig.get_solo()
        applicatie_url = (
            f"{config.authorizations_api_service.api_root}/applicaties/{uuid}"
        )
        webhook_url = reverse("catalogi:notificaties-webhook")
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "destroy",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertEqual(Applicatie.objects.filter(client_ids=["id1"]).count(), 0)

    @requests_mock.Mocker()
    def test_handle_client_error(self, m):
        applicatie = Applicatie.objects.create(
            client_ids=["id1"], label="for delete", heeft_alle_autorisaties=True
        )
        uuid = applicatie.uuid
        config = AuthorizationsConfig.get_solo()
        applicatie_url = (
            f"{config.authorizations_api_service.api_root}/applicaties/{uuid}"
        )
        webhook_url = reverse("catalogi:notificaties-webhook")
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "create",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        m.get(applicatie_url, status_code=403)

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_handle_service_error(self):
        applicatie = Applicatie.objects.create(
            client_ids=["id1"], label="for delete", heeft_alle_autorisaties=True
        )
        uuid = applicatie.uuid
        applicatie_url = (
            f"'https://autorisaties-api.vng.cloud/api/v99/applicaties/{uuid}"
        )
        webhook_url = reverse("catalogi:notificaties-webhook")
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "create",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
