# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings, tag

from freezegun.api import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ...zaken.tests.factories import ZaakFactory
from ..api.cloudevents import BESLUIT_VERWERKT
from ..constants import VervalRedenen
from ..models import Besluit


@tag("convenience-endpoints", "cloudevents")
@freeze_time("2025-10-10")
@patch("notifications_api_common.tasks.send_cloudevent.delay")
@patch(
    "notifications_api_common.cloudevents.uuid.uuid4",
    lambda: "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
)
@override_settings(NOTIFICATIONS_SOURCE="oz-test", ENABLE_CLOUD_EVENTS=True)
class BesluitConvenienceCloudEventTest(
    NotificationsConfigMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    def test_besluiten_verwerken_cloudevent(self, mock_send_cloudevent):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        catalogus_url = reverse(besluittype.catalogus)

        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        zaaktype_url = reverse(zaak.zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)

        besluittype.informatieobjecttypen.add(informatieobjecttype)
        besluittype.zaaktypen.add(zaak.zaaktype)

        informatieobject_1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_1 = reverse(informatieobject_1)

        informatieobject_2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_2 = reverse(informatieobject_2)

        url = reverse("verwerkbesluit-list")

        data = {
            "besluit": {
                "verantwoordelijkeOrganisatie": "517439943",  # RSIN
                "besluittype": f"http://testserver{besluittype_url}",
                "zaak": f"http://testserver{zaak_url}",
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

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        besluit = Besluit.objects.get()
        besluit_url = reverse(besluit)

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": BESLUIT_VERWERKT,
                "subject": str(besluit.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": besluit_url,
                "datacontenttype": "application/json",
                "data": {
                    "verantwoordelijkeOrganisatie": "517439943",
                    "besluittype": f"http://testserver{besluittype_url}",
                    "besluittype.catalogus": f"http://testserver{catalogus_url}",
                    "zaak.zaaktype": f"http://testserver{zaaktype_url}",
                    "informatieobjecten.iotype": [  # TODO duplicates?
                        f"http://testserver{informatieobjecttype_url}",
                        f"http://testserver{informatieobjecttype_url}",
                    ],
                },
            }
        )
