# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
import base64
from unittest.mock import call, patch

from django.conf import settings
from django.test import override_settings, tag

from freezegun.api import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.zaken.api.cloudevents import ZAAK_GEMUTEERD
from openzaak.components.zaken.signals import scheduled
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin

from ...zaken.tests.factories import StatusFactory, ZaakFactory
from ..api.cloudevents import DOCUMENT_GEREGISTREERD
from ..models import EnkelvoudigInformatieObject
from .utils import (
    get_operation_url,
)


@tag("convenience-endpoints", "cloudevents")
@freeze_time("2025-10-10")
@patch("notifications_api_common.tasks.send_cloudevent.delay")
@patch(
    "notifications_api_common.cloudevents.uuid.uuid4",
    lambda: "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
)
@override_settings(
    NOTIFICATIONS_SOURCE="oz-test", ENABLE_CLOUD_EVENTS=True, SITE_DOMAIN="testserver"
)
class DocumentConvenienceCloudEventTest(
    NotificationsConfigMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        scheduled.set(False)

    def test_document_registreren_cloudevent(self, mock_send_cloudevent):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        catalogus_url = reverse(informatieobjecttype.catalogus)

        zaak = ZaakFactory.create(bronorganisatie="000000000")
        zaak_url = reverse(zaak)
        zaaktype_url = reverse(zaak.zaaktype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=informatieobjecttype
        )

        _status = StatusFactory.create(zaak=zaak)
        status_url = reverse(_status)

        url = get_operation_url("registreerdocument_create")

        data = {
            "enkelvoudiginformatieobject": {
                "identificatie": "AMS20180701001",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-07-01",
                "titel": "text_extra.txt",
                "auteur": "ANONIEM",
                "formaat": "text/plain",
                "taal": "dut",
                "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            "zaakinformatieobject": {
                "zaak": f"http://testserver{zaak_url}",
                "titel": "string",
                "beschrijving": "string",
                "vernietigingsdatum": "2019-08-24T14:15:22Z",
                "status": f"http://testserver{status_url}",
            },
        }
        mock_send_cloudevent.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 2)

        document = EnkelvoudigInformatieObject.objects.get()
        document_url = reverse(document)

        mock_send_cloudevent.assert_has_calls(
            [
                call(
                    {
                        "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                        "source": settings.NOTIFICATIONS_SOURCE,
                        "specversion": settings.CLOUDEVENT_SPECVERSION,
                        "type": ZAAK_GEMUTEERD,
                        "subject": str(zaak.uuid),
                        "time": "2025-10-10T00:00:00Z",
                        "dataref": zaak_url,
                        "datacontenttype": "application/json",
                        "data": {
                            "bronorganisatie": "000000000",
                            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
                            "zaaktype": f"http://testserver{zaaktype_url}",
                            "zaaktype.catalogus": f"http://testserver{reverse(zaak.zaaktype.catalogus)}",
                        },
                    }
                ),
                call(
                    {
                        "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                        "source": settings.NOTIFICATIONS_SOURCE,
                        "specversion": settings.CLOUDEVENT_SPECVERSION,
                        "type": DOCUMENT_GEREGISTREERD,
                        "subject": str(document.uuid),
                        "time": "2025-10-10T00:00:00Z",
                        "dataref": document_url,
                        "datacontenttype": "application/json",
                        "data": {
                            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                            "informatieobjecttype.catalogus": f"http://testserver{catalogus_url}",
                            "bronorganisatie": "159351741",
                            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                            "zaak.zaaktype": f"http://testserver{zaaktype_url}",
                        },
                    }
                ),
            ],
            any_order=True,
        )
