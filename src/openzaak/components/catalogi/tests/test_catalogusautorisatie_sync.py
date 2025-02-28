# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from unittest.mock import call, patch

from django.contrib.sites.models import Site
from django.test import TestCase, override_settings, tag

from freezegun import freeze_time
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    CatalogusAutorisatieFactory,
)
from openzaak.components.catalogi.models import InformatieObjectType, ZaakType
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin


@freeze_time("2024-01-01T12:00:00Z")
@override_settings(NOTIFICATIONS_DISABLED=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
@tag("gh-1661")
class CatalogusAutorisatieSyncTestCase(NotificationsConfigMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        cls.catalogus1 = CatalogusFactory.create()
        cls.catalogus2 = CatalogusFactory.create()
        cls.applicatie1 = ApplicatieFactory.create()
        cls.applicatie2 = ApplicatieFactory.create()

        cls.catalogus_autorisatie1 = CatalogusAutorisatieFactory.create(
            applicatie=cls.applicatie1,
            catalogus=cls.catalogus1,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        cls.catalogus_autorisatie2 = CatalogusAutorisatieFactory.create(
            applicatie=cls.applicatie1,
            catalogus=cls.catalogus2,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        cls.catalogus_autorisatie3 = CatalogusAutorisatieFactory.create(
            applicatie=cls.applicatie2,
            catalogus=cls.catalogus1,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        cls.catalogus_autorisatie4 = CatalogusAutorisatieFactory.create(
            applicatie=cls.applicatie2,
            catalogus=cls.catalogus2,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

        # unrelated, should not be triggered
        cls.applicatie3 = ApplicatieFactory.create()
        CatalogusAutorisatieFactory.create(
            applicatie=cls.applicatie3,
            catalogus=cls.catalogus2,
            component=ComponentTypes.zrc,
            scopes=["zaken.lezen"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )

    def test_zaaktype_save_sync_send_notificaties(self, mock_notif_send):
        # Create a ZaakType to trigger the sync operation
        with self.captureOnCommitCallbacks(execute=True):
            ZaakTypeFactory.create(catalogus=self.catalogus1)

        self.assertEqual(mock_notif_send.call_count, 2)

        mock_notif_send.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie1)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie1)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie2)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie2)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
            ],
            any_order=True,
        )

    def test_zaaktype_bulk_create_sync_send_notificaties(self, mock_notif_send):
        # Bulk create ZaakTypen to trigger the sync operation
        with self.captureOnCommitCallbacks(execute=True):
            ZaakType.objects.bulk_create(
                [
                    ZaakTypeFactory.build(catalogus=self.catalogus1),
                    ZaakTypeFactory.build(catalogus=self.catalogus2),
                ]
            )

        self.assertEqual(mock_notif_send.call_count, 3)

        mock_notif_send.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie1)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie1)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie2)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie2)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie3)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie3)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
            ],
            any_order=True,
        )

    def test_besluittype_save_sync_send_notificaties(self, mock_notif_send):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus1)

        # Create a BesluitType to trigger the sync operation
        with self.captureOnCommitCallbacks(execute=True):
            BesluitTypeFactory.create(catalogus=self.catalogus1, zaaktypen=[zaaktype])

        self.assertEqual(mock_notif_send.call_count, 2)

        mock_notif_send.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie1)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie1)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie2)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie2)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
            ],
            any_order=True,
        )

    def test_informatieobjecttype_save_sync_send_notificaties(self, mock_notif_send):
        # Create a BesluitType to trigger the sync operation
        with self.captureOnCommitCallbacks(execute=True):
            InformatieObjectTypeFactory.create(catalogus=self.catalogus1)

        self.assertEqual(mock_notif_send.call_count, 2)

        mock_notif_send.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie1)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie1)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie2)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie2)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
            ],
            any_order=True,
        )

    def test_informatieobjecttype_bulk_create_sync_send_notificaties(
        self, mock_notif_send
    ):
        # Bulk create BesluitTypen to trigger the sync operation
        with self.captureOnCommitCallbacks(execute=True):
            InformatieObjectType.objects.bulk_create(
                [
                    InformatieObjectTypeFactory.build(catalogus=self.catalogus1),
                    InformatieObjectTypeFactory.build(catalogus=self.catalogus2),
                ]
            )

        self.assertEqual(mock_notif_send.call_count, 3)

        mock_notif_send.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie1)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie1)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie2)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie2)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
                call(
                    {
                        "kanaal": "autorisaties",
                        "hoofdObject": f"http://testserver{reverse(self.applicatie3)}",
                        "resource": "applicatie",
                        "resourceUrl": f"http://testserver{reverse(self.applicatie3)}",
                        "actie": "update",
                        "aanmaakdatum": "2024-01-01T12:00:00Z",
                        "kenmerken": {},
                    }
                ),
            ],
            any_order=True,
        )
