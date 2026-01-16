# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings, tag

import requests_mock
from freezegun.api import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ...documenten.tests.utils import get_informatieobjecttype_response
from ..api.cloudevents import (
    ZAAK_AFGESLOTEN,
    ZAAK_BIJGEWERKT,
    ZAAK_GEREGISTREERD,
    ZAAK_OPGESCHORT,
    ZAAK_VERLENGD,
)
from ..models import Zaak
from .factories import ZaakFactory
from .test_rol import BETROKKENE
from .utils import (
    get_catalogus_response,
    get_operation_url,
    get_roltype_response,
    get_statustype_response,
    get_zaaktype_response,
)


@tag("convenience-endpoints", "cloudevents")
@freeze_time("2025-10-10")
@patch("notifications_api_common.tasks.send_cloudevent.delay")
@patch(
    "notifications_api_common.cloudevents.uuid.uuid4",
    lambda: "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
)
@override_settings(NOTIFICATIONS_SOURCE="oz-test", ENABLE_CLOUD_EVENTS=True)
class ZaakConvenienceCloudEventTest(
    NotificationsConfigMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        self.zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=informatieobjecttype.catalogus
        )
        self.zaaktype_url = self.check_for_instance(self.zaaktype)
        self.catalogus_url = self.check_for_instance(self.zaaktype.catalogus)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=self.zaaktype, informatieobjecttype=informatieobjecttype
        )

        roltype = RolTypeFactory(zaaktype=self.zaaktype)
        self.roltype_url = self.check_for_instance(roltype)

        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)
        self.statustype_url = self.check_for_instance(statustype)

        eindstatustype = StatusTypeFactory.create(zaaktype=self.zaaktype)

        self.eindstatustype_url = self.check_for_instance(eindstatustype)

        informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        self.informatieobject_url = self.check_for_instance(informatieobject)

        resultaattype = ResultaatTypeFactory(
            zaaktype=self.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        self.resultaattype_url = self.check_for_instance(resultaattype)

        self.zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            bronorganisatie=517439943,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            verantwoordelijke_organisatie=517439943,
        )
        self.zaak_url = reverse(self.zaak)

    def test_zaak_registreren_cloudevent(self, mock_send_cloudevent):
        url = get_operation_url("registreerzaak_create")

        data = {
            "zaak": {
                "zaaktype": self.zaaktype_url,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "111222333",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2011-06-11",
                "startdatum": "2018-06-11",
                "toelichting": "toelichting",
            },
            "rollen": [
                {
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": self.roltype_url,
                    "roltoelichting": "awerw",
                }
            ],
            "zaakinformatieobjecten": [
                {
                    "informatieobject": self.informatieobject_url,
                    "titel": "string",
                    "beschrijving": "string",
                    "vernietigingsdatum": "2011-08-24T14:15:22Z",
                }
            ],
            "zaakobjecten": [
                {
                    "objectType": ZaakobjectTypes.overige,
                    "objectTypeOverige": "test",
                    "relatieomschrijving": "test",
                    "objectIdentificatie": {"overigeData": {"someField": "some value"}},
                },
                {
                    "objectType": ZaakobjectTypes.overige,
                    "objectTypeOverige": "test",
                    "relatieomschrijving": "test",
                    "objectIdentificatie": {"overigeData": {"someField": "test"}},
                },
            ],
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get(bronorganisatie="111222333")
        zaak_url = reverse(zaak)

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_GEREGISTREERD,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "111222333",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": self.zaaktype_url,
                    "zaaktype.catalogus": self.catalogus_url,
                },
            }
        )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_zaak_registreren_cloudevents_external_urls(self, mock_send_cloudevent):
        url = get_operation_url("registreerzaak_create")

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        zaaktype_url = "https://externe.catalogus.nl/api/v1/zaaktypen/1"
        catalogus_url = "https://externe.catalogus.nl/api/v1/catalogi/1"
        roltype_url = "https://externe.catalogus.nl/api/v1/roltypen/1"
        statustype_url = "https://externe.catalogus.nl/api/v1/statustypen/1"
        informatieobjecttype_url = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/1"
        )

        informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype_url
        )
        informatieobject_url = self.check_for_instance(informatieobject)

        data = {
            "zaak": {
                "zaaktype": zaaktype_url,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "111222333",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2011-06-11",
                "startdatum": "2018-06-11",
                "toelichting": "toelichting",
            },
            "rollen": [
                {
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": roltype_url,
                    "roltoelichting": "awerw",
                }
            ],
            "zaakinformatieobjecten": [
                {
                    "informatieobject": informatieobject_url,
                    "titel": "string",
                    "beschrijving": "string",
                    "vernietigingsdatum": "2011-08-24T14:15:22Z",
                }
            ],
            "zaakobjecten": [
                {
                    "objectType": ZaakobjectTypes.overige,
                    "objectTypeOverige": "test",
                    "relatieomschrijving": "test",
                    "objectIdentificatie": {"overigeData": {"someField": "some value"}},
                },
                {
                    "objectType": ZaakobjectTypes.overige,
                    "objectTypeOverige": "test",
                    "relatieomschrijving": "test",
                    "objectIdentificatie": {"overigeData": {"someField": "test"}},
                },
            ],
            "status": {
                "statustype": statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            with requests_mock.Mocker() as m:
                mock_ztc_oas_get(m)
                m.get(
                    zaaktype_url,
                    json=get_zaaktype_response(
                        catalogus_url,
                        zaaktype_url,
                        informatieobjecttypen=[informatieobjecttype_url],
                    ),
                )
                m.get(
                    catalogus_url,
                    json=get_catalogus_response(catalogus_url, zaaktype_url),
                )
                m.get(roltype_url, json=get_roltype_response(roltype_url, zaaktype_url))
                m.get(
                    statustype_url,
                    json=get_statustype_response(statustype_url, zaaktype_url),
                )
                m.get(
                    informatieobjecttype_url,
                    json=get_informatieobjecttype_response(
                        catalogus_url, informatieobjecttype_url
                    ),
                )

                response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get(bronorganisatie="111222333")
        zaak_url = reverse(zaak)

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_GEREGISTREERD,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "111222333",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": zaaktype_url,
                    "zaaktype.catalogus": catalogus_url,
                },
            }
        )

    def test_zaak_opschorten_cloudevent(self, mock_send_cloudevent):
        url = reverse(
            "zaakopschorten",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

        data = {
            "zaak": {
                "opschorting": {"indicatie": True, "reden": "test"},
            },
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get()
        zaak_url = reverse(zaak)

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_OPGESCHORT,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": self.zaaktype_url,
                    "zaaktype.catalogus": self.catalogus_url,
                },
            }
        )

    def test_zaak_bijwerken_cloudevent(self, mock_send_cloudevent):
        url = reverse(
            "zaakbijwerken",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

        data = {
            "zaak": {
                "toelichting": "toelichting",
            },
            "rollen": [
                {
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.natuurlijk_persoon,
                    "roltype": self.roltype_url,
                    "roltoelichting": "awerw",
                }
            ],
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get()

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_BIJGEWERKT,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": self.zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": self.zaaktype_url,
                    "zaaktype.catalogus": self.catalogus_url,
                },
            }
        )

    def test_zaak_verlengen_cloudevent(self, mock_send_cloudevent):
        url = reverse(
            "zaakverlengen",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

        data = {
            "zaak": {
                "verlenging": {"reden": "reden", "duur": "P5D"},
            },
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get()

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_VERLENGD,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": self.zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": self.zaaktype_url,
                    "zaaktype.catalogus": self.catalogus_url,
                },
            }
        )

    def test_zaak_afsluiten_cloudevent(self, mock_send_cloudevent):
        url = reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid})

        data = {
            "zaak": {"toelichting": "toelichting"},
            "status": {
                "statustype": self.eindstatustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
                "statustoelichting": "Afgesloten via test",
            },
            "resultaat": {
                "resultaattype": self.resultaattype_url,
                "toelichting": "Test resultaat",
            },
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(mock_send_cloudevent.call_count, 1)

        zaak = Zaak.objects.get()

        mock_send_cloudevent.assert_called_once_with(
            {
                "id": "f347fd1f-dac1-4870-9dd0-f6c00edf4bf7",
                "source": settings.NOTIFICATIONS_SOURCE,
                "specversion": settings.CLOUDEVENT_SPECVERSION,
                "type": ZAAK_AFGESLOTEN,
                "subject": str(zaak.uuid),
                "time": "2025-10-10T00:00:00Z",
                "dataref": self.zaak_url,
                "datacontenttype": "application/json",
                "data": {
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "zaaktype": self.zaaktype_url,
                    "zaaktype.catalogus": self.catalogus_url,
                },
            }
        )

    def test_cloudevent_not_send(self, mock_send_cloudevent):
        url = reverse(
            "zaakbijwerken",
            kwargs={
                "uuid": self.zaak.uuid,
            },
        )

        data = {
            "zaak": {
                "toelichting": "toelichting",
            },
            "status": {
                "statustype": self.statustype_url,
                "datumStatusGezet": "2011-01-01T00:00:00",
            },
        }

        with (
            self.subTest("enable cloudevents false"),
            override_settings(ENABLE_CLOUD_EVENTS=False),
        ):
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            mock_send_cloudevent.assert_not_called()

        with (
            self.subTest("no notifcation source"),
            override_settings(ENABLE_CLOUD_EVENTS=True, NOTIFICATIONS_SOURCE=""),
        ):
            data["status"]["datumStatusGezet"] = "2011-01-01T00:00:01"

            response = self.client.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            mock_send_cloudevent.assert_not_called()
