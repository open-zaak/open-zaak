from datetime import date

from django.test import override_settings
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    ComponentTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.besluiten.api.scopes import SCOPE_BESLUITEN_AANMAKEN
from openzaak.components.besluiten.constants import VervalRedenen
from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class BesluitVerwerkenAuthTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("verwerkbesluit-list")
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim

    @classmethod
    def setUpClass(cls):
        APITestCase.setUpClass()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id, defaults={"secret": cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label="for test",
            heeft_alle_autorisaties=False,
        )

        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        cls.informatieobjecttype_url = cls.check_for_instance(cls.informatieobjecttype)

        cls.besluittype = BesluitTypeFactory.create(
            concept=False, catalogus=cls.informatieobjecttype.catalogus
        )
        cls.besluittype.informatieobjecttypen.add(cls.informatieobjecttype)

        cls.besluittype_url = cls.check_for_instance(cls.besluittype)

    def _add_besluiten_auth(self, besluittype=None, zaaktype=None, scopes=None):
        if scopes is None:
            scopes = []

        self.autorisatie = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=[SCOPE_BESLUITEN_AANMAKEN] + scopes,
            zaaktype=zaaktype if zaaktype else "",
            informatieobjecttype="",
            besluittype=self.besluittype_url if besluittype is None else besluittype,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def _add_catalogi_auth(self, component: ComponentTypes, catalogus, scopes):
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=component,
            scopes=scopes,
            catalogus=catalogus,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def setUp(self):
        super().setUp()

        informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        informatieobject_url = reverse(informatieobject)

        self.content = {
            "besluit": {
                "verantwoordelijke_organisatie": "517439943",
                "identificatie": "123123",
                "besluittype": self.besluittype_url,
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
            "besluitinformatieobjecten": [
                {
                    "informatieobject": f"http://testserver{informatieobject_url}",
                }
            ],
        }

    def test_verwerk_besluit(self):
        self._add_besluiten_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_verwerk_besluit_no_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_verwerk_besluit_no_besluittype_in_auth(self):
        self._add_besluiten_auth(besluittype="")

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_verwerk_besluit_with_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.brc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_BESLUITEN_AANMAKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_with_closed_zaak(self):
        self._add_besluiten_auth()

        zaak = ZaakFactory.create(
            einddatum=timezone.now(), zaaktype__catalogus=self.besluittype.catalogus
        )
        zaak_url = reverse(zaak)
        self.besluittype.zaaktypen.add(zaak.zaaktype)

        self.assertTrue(zaak.is_closed)

        content = self.content.copy()
        content["besluit"]["zaak"] = f"http://testserver{zaak_url}"

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(
            response.data["detail"],
            "Je mag geen gegevens aanpassen van een gesloten zaak.",
        )

    def test_register_with_closed_zaak_with_force_scope(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now(), zaaktype__catalogus=self.besluittype.catalogus
        )
        zaak_url = reverse(zaak)
        self.besluittype.zaaktypen.add(zaak.zaaktype)

        self.assertTrue(zaak.is_closed)

        self._add_besluiten_auth(
            scopes=[SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN],
            zaaktype=f"http://testserver{reverse(zaak.zaaktype)}",
        )

        content = self.content.copy()
        content["besluit"]["zaak"] = f"http://testserver{zaak_url}"

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class BesluitVerwerkenValidationTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("verwerkbesluit-list")
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        self.informatieobjecttype_url = reverse(self.informatieobjecttype)

        self.besluittype = BesluitTypeFactory.create(
            concept=False, catalogus=self.informatieobjecttype.catalogus
        )
        self.besluittype.informatieobjecttypen.add(self.informatieobjecttype)

        self.besluittype_url = reverse(self.besluittype)

        self.informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        self.informatieobject_url = reverse(self.informatieobject)

        self.besluit = {
            "verantwoordelijke_organisatie": "517439943",
            "identificatie": "123123",
            "besluittype": f"http://testserver{self.besluittype_url}",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        self.besluitinformatieobject = {
            "informatieobject": f"http://testserver{self.informatieobject_url}",
        }

        self.besluitinformatieobjecten = [self.besluitinformatieobject]

    def test_verwerk_besluit(self):
        content = {
            "besluit": self.besluit,
            "besluitinformatieobjecten": self.besluitinformatieobjecten,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        besluit = Besluit.objects.get()

        self.assertEqual(besluit.verantwoordelijke_organisatie, "517439943")
        self.assertEqual(besluit.besluittype, self.besluittype)
        self.assertEqual(besluit.zaak, None)
        self.assertEqual(besluit.datum, date(2018, 9, 6))
        self.assertEqual(besluit.toelichting, "Vergunning verleend.")
        self.assertEqual(besluit.ingangsdatum, date(2018, 10, 1))
        self.assertEqual(besluit.vervaldatum, date(2018, 11, 1))
        self.assertEqual(besluit.vervalreden, VervalRedenen.tijdelijk)

        besluitinformatieobject = BesluitInformatieObject.objects.get()

        self.assertEqual(besluitinformatieobject.besluit, besluit)
        self.assertEqual(
            besluitinformatieobject.informatieobject, self.informatieobject.canonical
        )

        expected_besluit_url = reverse(besluit)
        expected_besluitinformatieobject_url = reverse(besluitinformatieobject)

        expected_response = {
            "besluit": {
                "besluittype": f"http://testserver{self.besluittype_url}",
                "bestuursorgaan": "",
                "datum": "2018-09-06",
                "identificatie": "123123",
                "ingangsdatum": "2018-10-01",
                "publicatiedatum": None,
                "toelichting": "Vergunning verleend.",
                "uiterlijkeReactiedatum": None,
                "url": f"http://testserver{expected_besluit_url}",
                "verantwoordelijkeOrganisatie": "517439943",
                "vervaldatum": "2018-11-01",
                "vervalreden": "tijdelijk",
                "vervalredenWeergave": "Besluit met tijdelijke werking",
                "verzenddatum": None,
                "zaak": "",
            },
            "besluitinformatieobjecten": [
                {
                    "besluit": f"http://testserver{expected_besluit_url}",
                    "informatieobject": f"http://testserver{self.informatieobject_url}",
                    "url": f"http://testserver{expected_besluitinformatieobject_url}",
                }
            ],
        }
        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_besluittype_zaaktype_not_in_same_catalogus(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        content = {
            "besluit": self.besluit | {"zaak": f"http://testserver{zaak_url}"},
            "besluitinformatieobjecten": self.besluitinformatieobjecten,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "besluit.nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    def test_no_besluittype_informatieobjecttype_relation(self):
        self.besluittype.informatieobjecttypen.clear()

        content = {
            "besluit": self.besluit,
            "besluitinformatieobjecten": self.besluitinformatieobjecten,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-besluittype-informatieobjecttype-relation"
        )

    def test_besluit_informatieobject_unique_together(self):
        content = {
            "besluit": self.besluit,
            "besluitinformatieobjecten": [
                self.besluitinformatieobject,
                self.besluitinformatieobject,
            ],
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_invalid_informatieobject(self):
        content = {
            "besluit": self.besluit,
            "besluitinformatieobjecten": [
                {
                    "informatieobject": "http://testserver/documenten/api/v1/enkelvoudiginformatieobjecten/852e5ca8-cdbe-42ab-ae80-aa79a15cc9e4"
                },
            ],
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(
            response, "besluitinformatieobjecten.0.informatieobject"
        )
        self.assertEqual(error["code"], "does_not_exist")
