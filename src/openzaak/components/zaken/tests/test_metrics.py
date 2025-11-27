# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from unittest.mock import MagicMock, patch

from rest_framework.test import APITestCase
from vng_api_common.constants import (
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin

from ..metrics import zaken_create_counter, zaken_delete_counter, zaken_update_counter
from .factories import ZaakFactory, ZaakTypeFactory
from .utils import (
    ZAAK_WRITE_KWARGS,
)


class ZakenTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch.object(zaken_create_counter, "add", wraps=zaken_create_counter.add)
    def test_zaken_create_counter(self, mock_add: MagicMock):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        self.client.post(
            reverse("zaak-list"),
            {
                "zaaktype": f"http://testserver{zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )
        mock_add.assert_called_once_with(1)

    @patch.object(zaken_update_counter, "add", wraps=zaken_update_counter.add)
    def test_zaken_update_counter(self, mock_add: MagicMock):
        zaak = ZaakFactory.create()
        self.client.patch(
            reverse(
                "zaak-detail",
                kwargs={"uuid": str(zaak.uuid)},
            ),
            {},
            **ZAAK_WRITE_KWARGS,
        )
        mock_add.assert_called_once_with(1)

    @patch.object(zaken_delete_counter, "add", wraps=zaken_delete_counter.add)
    def test_zaken_delete_counter(self, mock_add: MagicMock):
        zaak = ZaakFactory.create()
        self.client.delete(
            reverse(
                "zaak-detail",
                kwargs={"uuid": str(zaak.uuid)},
            ),
            {},
        )
        mock_add.assert_called_once_with(1)
