# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid as _uuid
from unittest import skip

from django.conf import settings

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, AuthorizationsConfig
from vng_api_common.constants import VertrouwelijkheidsAanduiding

from openzaak.utils.tests import JWTAuthMixin, mock_client


@skip("Authorization component is internal. Webhooks are not used")
class HandleAuthNotifTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_handle_create_auth(self):
        config = AuthorizationsConfig.get_solo()
        uuid = _uuid.uuid4()
        applicatie_url = f"{config.api_root}applicaties/{uuid}"
        webhook_url = reverse("notificaties-webhook")

        responses = {
            applicatie_url: {
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
                        "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                        "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    }
                ],
            }
        }
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "create",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }
        with mock_client(responses):
            response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        applicatie = Applicatie.objects.get(client_ids=["id1"])

        self.assertEqual(applicatie.uuid, uuid)

    def test_handle_update_auth(self):
        applicatie = Applicatie.objects.create(
            client_ids=["id1"], label="before", heeft_alle_autorisaties=True
        )
        uuid = applicatie.uuid
        config = AuthorizationsConfig.get_solo()
        applicatie_url = f"{config.api_root}/applicaties/{uuid}"

        self.assertEqual(applicatie.autorisaties.count(), 0)

        # webhook_url = get_operation_url('notification_receive')
        webhook_url = reverse(
            "notificaties-webhook",
            kwargs={"version": settings.REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        responses = {
            applicatie_url: {
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
                        "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                        "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    }
                ],
            }
        }
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "partial_update",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        with mock_client(responses):
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
        applicatie_url = f"{config.api_root}/applicaties/{uuid}"
        webhook_url = reverse(
            "notificaties-webhook",
            kwargs={"version": settings.REST_FRAMEWORK["DEFAULT_VERSION"]},
        )
        data = {
            "kanaal": "autorisaties",
            "hoofdObject": applicatie_url,
            "resource": "applicatie",
            "resourceUrl": applicatie_url,
            "actie": "delete",
            "aanmaakdatum": "2012-01-14T00:00:00Z",
            "kenmerken": {},
        }

        response = self.client.post(webhook_url, data)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertEqual(Applicatie.objects.filter(client_ids=["id1"]).count(), 0)
