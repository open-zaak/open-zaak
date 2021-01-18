# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from dateutil import parser
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.utils.tests import JWTAuthMixin

from ..models import Zaak
from .utils import ZAAK_WRITE_KWARGS, get_operation_url, utcdatetime

VERANTWOORDELIJKE_ORGANISATIE = "517439943"

TEST_DATA = {
    "id": 9966,
    "last_status": "o",
    "adres": "Oosterdok 51, 1011 Amsterdam, Netherlands",
    "datetime": "2018-05-28T09:05:08.732587+02:00",
    "text": "test",
    "waternet_soort_boot": "Nee",
    "waternet_rederij": "Onbekend",
    "waternet_naam_boot": "De Amsterdam",
    "datetime_overlast": "2018-05-28T08:35:11+02:00",
    "email": "",
    "phone_number": "",
    "source": "Telefoon 14020",
    "text_extra": "",
    "image": None,
    "main_category": "",
    "sub_category": "Geluid",
    "ml_cat": "melding openbare ruimte",
    "stadsdeel": "Centrum",
    "coordinates": "POINT (4.910649523925713 52.37240093589432)",
    "verantwoordelijk": "Waternet",
}


class Application:
    def __init__(self, client, data: dict):
        self.client = client

        self.data = data
        self.references = {}

    def store_notification(self):
        # registreer zaak & zet statussen, resultaat
        self.registreer_zaak()
        self.registreer_domein_data()
        self.registreer_klantcontact()
        self.zet_statussen_resultaat()

    def registreer_zaak(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        zaak_create_url = get_operation_url("zaak_create")

        created = parser.parse(self.data["datetime"])
        intern_id = self.data["id"]

        response = self.client.post(
            zaak_create_url,
            {
                "zaaktype": f"http://testserver{zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
                "identificatie": f"WATER_{intern_id}",
                "registratiedatum": created.strftime("%Y-%m-%d"),
                "startdatum": created.strftime("%Y-%m-%d"),
                "toelichting": self.data["text"],
                "zaakgeometrie": self.data["coordinates"],
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.references["zaak_url"] = response.json()["url"]
        self.references["zaaktype"] = zaaktype

    def zet_statussen_resultaat(self):
        statustype = StatusTypeFactory.create(zaaktype=self.references["zaaktype"])
        statustype_url = reverse(statustype)
        statustype_overlast_geconstateerd = StatusTypeFactory.create(
            zaaktype=self.references["zaaktype"]
        )
        statustype_overlast_geconstateerd_url = reverse(
            statustype_overlast_geconstateerd
        )
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=self.references["zaaktype"],
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        resultaattype_url = reverse(resultaattype)
        status_create_url = get_operation_url("status_create")
        resultaat_create_url = get_operation_url("resultaat_create")
        created = parser.parse(self.data["datetime"])

        self.client.post(
            status_create_url,
            {
                "zaak": self.references["zaak_url"],
                "statustype": f"http://testserver{statustype_url}",
                "datumStatusGezet": created.isoformat(),
            },
        )

        self.client.post(
            resultaat_create_url,
            {
                "zaak": self.references["zaak_url"],
                "resultaattype": f"http://testserver{resultaattype_url}",
                "toelichting": "",
            },
        )

        self.client.post(
            status_create_url,
            {
                "zaak": self.references["zaak_url"],
                "statustype": f"http://testserver{statustype_overlast_geconstateerd_url}",
                "datumStatusGezet": parser.parse(
                    self.data["datetime_overlast"]
                ).isoformat(),
            },
        )

        self.references["statustype"] = statustype
        self.references[
            "statustype_overlast_geconstateerd"
        ] = statustype_overlast_geconstateerd

    def registreer_domein_data(self):
        eigenschap_objecttype = EigenschapFactory.create(
            eigenschapnaam="melding_type", zaaktype=self.references["zaaktype"]
        )
        eigenschap_objecttype_url = reverse(eigenschap_objecttype)
        eigenschap_naam_boot = EigenschapFactory.create(
            eigenschapnaam="waternet_naam_boot", zaaktype=self.references["zaaktype"]
        )
        eigenschap_naam_boot_url = reverse(eigenschap_naam_boot)
        zaak_uuid = self.references["zaak_url"].rsplit("/")[-1]
        url = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak_uuid)

        self.client.post(
            url,
            {
                "zaak": self.references["zaak_url"],
                "eigenschap": f"http://testserver{eigenschap_objecttype_url}",
                "waarde": "overlast_water",
            },
        )
        self.client.post(
            url,
            {
                "zaak": self.references["zaak_url"],
                "eigenschap": f"http://testserver{eigenschap_naam_boot_url}",
                "waarde": TEST_DATA["waternet_naam_boot"],
            },
        )

        self.references["eigenschap_naam_boot"] = eigenschap_naam_boot

    def registreer_klantcontact(self):
        url = get_operation_url("klantcontact_create")
        self.client.post(
            url,
            {
                "zaak": self.references["zaak_url"],
                "datumtijd": self.data["datetime"],
                "kanaal": self.data["source"],
            },
        )


class US39IntegrationTestCase(JWTAuthMixin, APITestCase):
    """
    Simulate a full realistic flow.
    """

    heeft_alle_autorisaties = True

    def test_full_flow(self):
        app = Application(self.client, TEST_DATA)

        app.store_notification()

        zaak = Zaak.objects.get(identificatie="WATER_9966")
        self.assertEqual(zaak.toelichting, "test")
        self.assertEqual(zaak.zaakgeometrie.x, 4.910649523925713)
        self.assertEqual(zaak.zaakgeometrie.y, 52.37240093589432)

        self.assertEqual(zaak.status_set.count(), 2)

        last_status = zaak.status_set.order_by("-datum_status_gezet").first()
        self.assertEqual(last_status.statustype, app.references["statustype"])
        self.assertEqual(
            last_status.datum_status_gezet, utcdatetime(2018, 5, 28, 7, 5, 8, 732587)
        )

        first_status = zaak.status_set.order_by("datum_status_gezet").first()
        self.assertEqual(
            first_status.statustype, app.references["statustype_overlast_geconstateerd"]
        )
        self.assertEqual(
            first_status.datum_status_gezet, utcdatetime(2018, 5, 28, 6, 35, 11)
        )

        klantcontact = zaak.klantcontact_set.get()
        self.assertEqual(klantcontact.kanaal, "Telefoon 14020")
        self.assertEqual(
            klantcontact.datumtijd, utcdatetime(2018, 5, 28, 7, 5, 8, 732587)
        )

        eigenschappen = zaak.zaakeigenschap_set.all()
        self.assertEqual(eigenschappen.count(), 2)
        naam_boot = eigenschappen.get(eigenschap=app.references["eigenschap_naam_boot"])
        self.assertEqual(naam_boot.waarde, "De Amsterdam")
