# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import call, patch

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from notifications_api_common.models import FailedNotification, NotificationResponse
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.tests import mock_notification_send
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..constants import VervalRedenen
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@tag("notifications")
@freeze_time("2018-09-07T00:00:00Z")
@temp_private_root()
@override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
@patch("notifications_api_common.viewsets.send_notification.delay")
class SendNotifTestCase(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_send_notif_create_besluit(self, mock_notif):
        """
        Check if notifications will be send when Besluit is created
        """
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        mock_notif.assert_called_once_with(
            {
                "kanaal": "besluiten",
                "hoofdObject": data["url"],
                "resource": "besluit",
                "resourceUrl": data["url"],
                "actie": "create",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": "517439943",
                    "besluittype": f"http://testserver{besluittype_url}",
                    "besluittype.catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
                },
            },
            None,
        )

    @tag("convenience-endpoints")
    def test_send_notif_verwerk_besluit(self, mock_notif):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        besluittype.informatieobjecttypen.add(informatieobjecttype)

        informatieobject_1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_1 = reverse(informatieobject_1)

        informatieobject_2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_2 = reverse(informatieobject_2)

        url = reverse("besluiten:verwerkbesluit-list")

        data = {
            "besluit": {
                "verantwoordelijkeOrganisatie": "517439943",  # RSIN
                "besluittype": f"http://testserver{besluittype_url}",
                "identificatie": "123123",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
            "besluitinformatieobjecten": [
                {"informatieobject": f"http://testserver{informatieobject_url_1}"},
                {"informatieobject": f"http://testserver{informatieobject_url_2}"},
            ],
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()

        self.assertEqual(mock_notif.call_count, 3)
        mock_notif.assert_has_calls(
            [
                call(
                    {
                        "kanaal": "besluiten",
                        "hoofdObject": data["besluit"]["url"],
                        "resource": "besluit",
                        "resourceUrl": data["besluit"]["url"],
                        "actie": "create",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "verantwoordelijkeOrganisatie": "517439943",
                            "besluittype": f"http://testserver{besluittype_url}",
                            "besluittype.catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
                        },
                    },
                    None,
                ),
                call(
                    {
                        "kanaal": "besluiten",
                        "hoofdObject": data["besluit"]["url"],
                        "resource": "besluitinformatieobject",
                        "resourceUrl": data["besluitinformatieobjecten"][0]["url"],
                        "actie": "create",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "verantwoordelijkeOrganisatie": "517439943",
                            "besluittype": f"http://testserver{besluittype_url}",
                            "besluittype.catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
                        },
                    },
                    None,
                ),
                call(
                    {
                        "kanaal": "besluiten",
                        "hoofdObject": data["besluit"]["url"],
                        "resource": "besluitinformatieobject",
                        "resourceUrl": data["besluitinformatieobjecten"][1]["url"],
                        "actie": "create",
                        "aanmaakdatum": "2018-09-07T00:00:00Z",
                        "kenmerken": {
                            "verantwoordelijkeOrganisatie": "517439943",
                            "besluittype": f"http://testserver{besluittype_url}",
                            "besluittype.catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
                        },
                    },
                    None,
                ),
            ],
            any_order=True,
        )

    def test_send_notif_delete_resultaat(self, mock_notif):
        """
        Check if notifications will be send when resultaat is deleted
        """
        besluit = BesluitFactory.create()
        besluit_url = get_operation_url("besluit_read", uuid=besluit.uuid)
        besluittype_url = reverse(besluit.besluittype)
        bio = BesluitInformatieObjectFactory.create(besluit=besluit)
        bio_url = get_operation_url("besluitinformatieobject_delete", uuid=bio.uuid)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        mock_notif.assert_called_once_with(
            {
                "kanaal": "besluiten",
                "hoofdObject": f"http://testserver{besluit_url}",
                "resource": "besluitinformatieobject",
                "resourceUrl": f"http://testserver{bio_url}",
                "actie": "destroy",
                "aanmaakdatum": "2018-09-07T00:00:00Z",
                "kenmerken": {
                    "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                    "besluittype": f"http://testserver{besluittype_url}",
                    "besluittype.catalogus": f"http://testserver{reverse(besluit.besluittype.catalogus)}",
                },
            },
            None,
        )


@tag("notifications")
@requests_mock.Mocker()
@temp_private_root()
@override_settings(
    NOTIFICATIONS_DISABLED=False,
    LOG_NOTIFICATIONS_IN_DB=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
@freeze_time("2019-01-01T12:00:00Z")
class FailedNotificationTests(NotificationsConfigMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_besluit_create_fail_send_notification_create_db_entry(self, m):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        url = get_operation_url("besluit_create")
        data = {
            "verantwoordelijkeOrganisatie": "517439943",  # RSIN
            "besluittype": f"http://testserver{besluittype_url}",
            "identificatie": "123123",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": data["url"],
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": data["verantwoordelijkeOrganisatie"],
                "besluittype": f"http://testserver{besluittype_url}",
                "besluittype.catalogus": f"http://testserver{reverse(besluittype.catalogus)}",
            },
            "resource": "besluit",
            "resourceUrl": data["url"],
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_besluit_delete_fail_send_notification_create_db_entry(self, m):
        besluit = BesluitFactory.create()
        url = reverse(besluit, namespace="besluiten")

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{url}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(besluit.besluittype)}",
                "besluittype.catalogus": f"http://testserver{reverse(besluit.besluittype.catalogus)}",
            },
            "resource": "besluit",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_besluitinformatieobject_create_fail_send_notification_create_db_entry(
        self, m
    ):
        url = get_operation_url("besluitinformatieobject_create")

        besluit = BesluitFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit, namespace="besluiten")
        io_url = reverse(io)
        data = {
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": f"http://testserver{reverse(besluit, namespace='besluiten')}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(besluit.besluittype)}",
                "besluittype.catalogus": f"http://testserver{reverse(besluit.besluittype.catalogus)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": data["url"],
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)

    def test_besluitinformatieobject_delete_fail_send_notification_create_db_entry(
        self, m
    ):
        bio = BesluitInformatieObjectFactory.create()
        url = reverse(bio)

        mock_notification_send(m, status_code=403)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "destroy",
            "hoofdObject": f"http://testserver{reverse(bio.besluit)}",
            "kanaal": "besluiten",
            "kenmerken": {
                "verantwoordelijkeOrganisatie": bio.besluit.verantwoordelijke_organisatie,
                "besluittype": f"http://testserver{reverse(bio.besluit.besluittype)}",
                "besluittype.catalogus": f"http://testserver{reverse(bio.besluit.besluittype.catalogus)}",
            },
            "resource": "besluitinformatieobject",
            "resourceUrl": f"http://testserver{url}",
        }

        self.assertEqual(m.last_request.json(), message)
        self.assertEqual(FailedNotification.objects.count(), 1)
        self.assertEqual(NotificationResponse.objects.count(), 1)
