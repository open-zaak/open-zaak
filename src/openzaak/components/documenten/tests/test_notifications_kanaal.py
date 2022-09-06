# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from io import StringIO
from unittest.mock import call, patch

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import override_settings

from notifications_api_common.kanalen import KANAAL_REGISTRY, Kanaal
from rest_framework.test import APITestCase

from openzaak.notifications.tests.utils import NotificationsConfigMixin

from ..models import EnkelvoudigInformatieObject


@override_settings(IS_HTTPS=True)
class CreateNotifKanaalTestCase(NotificationsConfigMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        site = Site.objects.get_current()
        site.domain = "example.com"
        site.save()

        cls._configure_notifications()

        kanaal = Kanaal(label="dummy-kanaal", main_resource=EnkelvoudigInformatieObject)
        cls.addClassCleanup(lambda: KANAAL_REGISTRY.remove(kanaal))

    @patch("notifications_api_common.models.NotificationsConfig.get_client")
    def test_kanaal_create_with_name(self, mock_get_client):
        """
        Test is request to create kanaal is send with specified kanaal name
        """
        client = mock_get_client.return_value
        client.list.return_value = []

        stdout = StringIO()
        call_command(
            "register_kanalen", kanalen=["dummy-kanaal"], stdout=stdout,
        )

        client.create.assert_called_once_with(
            "kanaal",
            {
                "naam": "dummy-kanaal",
                "documentatieLink": "https://example.com/ref/kanalen/#dummy-kanaal",
                "filters": [],
            },
        )

    @patch("notifications_api_common.models.NotificationsConfig.get_client")
    def test_kanaal_create_without_name(self, mock_get_client):
        """
        Test is request to create kanaal is send for all registered kanalen
        """
        client = mock_get_client.return_value
        client.list.return_value = []

        stdout = StringIO()
        call_command(
            "register_kanalen", stdout=stdout,
        )

        client.create.assert_has_calls(
            [
                call(
                    "kanaal",
                    {
                        "naam": "autorisaties",
                        "documentatieLink": "https://example.com/ref/kanalen/#autorisaties",
                        "filters": [],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "besluiten",
                        "documentatieLink": "https://example.com/ref/kanalen/#besluiten",
                        "filters": ["verantwoordelijke_organisatie", "besluittype"],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "besluittypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#besluittypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "documenten",
                        "documentatieLink": "https://example.com/ref/kanalen/#documenten",
                        "filters": [
                            "bronorganisatie",
                            "informatieobjecttype",
                            "vertrouwelijkheidaanduiding",
                        ],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "dummy-kanaal",
                        "documentatieLink": "https://example.com/ref/kanalen/#dummy-kanaal",
                        "filters": [],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "informatieobjecttypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#informatieobjecttypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "zaaktypen",
                        "documentatieLink": "https://example.com/ref/kanalen/#zaaktypen",
                        "filters": ["catalogus"],
                    },
                ),
                call(
                    "kanaal",
                    {
                        "naam": "zaken",
                        "documentatieLink": "https://example.com/ref/kanalen/#zaken",
                        "filters": [
                            "bronorganisatie",
                            "zaaktype",
                            "vertrouwelijkheidaanduiding",
                        ],
                    },
                ),
            ]
        )
