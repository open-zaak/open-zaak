# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
"""
The tests cover reading, creating and filtering zaken with authenticatie_context.
The related US - https://github.com/open-zaak/open-zaak/issues/1733
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolOmschrijving, RolTypes
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import RolTypeFactory, ZaakTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..api.filters import MachtigingChoices
from ..api.serializers.authentication_context import (
    DigiDLevelOfAssurance,
    eHerkenningLevelOfAssurance,
    eHerkenningMandateRole,
    eHerkenningRepresenteeIdentifier,
)
from ..constants import IndicatieMachtiging
from ..models import NietNatuurlijkPersoon, Vestiging, Zaak
from .factories import RolFactory, ZaakFactory
from .utils import ZAAK_WRITE_KWARGS

ACTING_SUBJECT = (
    "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018"
    "@2D8FF1EF10279BC2643F376D89835151"
)


class FilterDigidTests(JWTAuthMixin, APITestCase):
    """
    tests for Zaken with Digid authenticatie context
    """

    heeft_alle_autorisaties = True
    url = reverse_lazy(Zaak)

    def test_filter_rol_machtiging(self):
        zaaktype = ZaakTypeFactory.create()
        roltype_initiator = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        roltype_belanghebbende = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )
        zaak_eigen, zaak_gemachtigde, zaak_machtiginggever = ZaakFactory.create_batch(
            3, zaaktype=zaaktype
        )
        RolFactory.create(
            zaak=zaak_eigen,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            roltoelichting="Created zaak",
            authenticatie_context={
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.middle,
            },
        )
        RolFactory.create(
            zaak=zaak_gemachtigde,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            authenticatie_context={
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifier_type": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        )
        RolFactory.create(
            zaak=zaak_machtiginggever,
            roltype=roltype_belanghebbende,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.machtiginggever,
            roltoelichting="Voogd",
        )

        with self.subTest(MachtigingChoices.eigen):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.eigen},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_eigen)}",
            )

        with self.subTest(MachtigingChoices.gemachtigde):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.gemachtigde},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_gemachtigde)}",
            )

        with self.subTest(MachtigingChoices.machtiginggever):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.machtiginggever},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_machtiginggever)}",
            )

    def test_filter_rol_machtiging_loa(self):
        zaaktype = ZaakTypeFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        zaak_loa_middle, zaak_loa_high = ZaakFactory.create_batch(2, zaaktype=zaaktype)
        RolFactory.create(
            zaak=zaak_loa_middle,
            roltype=roltype,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            authenticatie_context={
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifier_type": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        )
        RolFactory.create(
            zaak=zaak_loa_high,
            roltype=roltype,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            authenticatie_context={
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.high,
                "representee": {"identifier_type": "bsn", "identifier": "123456782"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        )

        with self.subTest(DigiDLevelOfAssurance.middle):
            response = self.client.get(
                self.url,
                {"rol__machtiging__loa": DigiDLevelOfAssurance.middle},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_loa_middle)}",
            )

        with self.subTest(DigiDLevelOfAssurance.high):
            response = self.client.get(
                self.url,
                {"rol__machtiging__loa": DigiDLevelOfAssurance.high},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)


class FilterEHerkenningTests(JWTAuthMixin, APITestCase):
    """
    tests for Rol with eHerkenning authenticatie context
    """

    heeft_alle_autorisaties = True
    url = reverse_lazy(Zaak)

    def test_rol_filter_machtiging(self):
        zaaktype = ZaakTypeFactory.create()
        roltype_initiator = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        roltype_belanghebbende = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )
        zaak_eigen, zaak_gemachtigde, zaak_machtiginggever = ZaakFactory.create_batch(
            3, zaaktype=zaaktype
        )
        RolFactory.create(
            zaak=zaak_eigen,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
            },
        )
        RolFactory.create(
            zaak=zaak_gemachtigde,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
                "representee": {
                    "identifier_type": eHerkenningRepresenteeIdentifier.bsn,
                    "identifier": "111222333",
                },
                "mandate": {
                    "role": eHerkenningMandateRole.bewindvoerder,
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ],
                },
            },
        )
        RolFactory.create(
            zaak=zaak_machtiginggever,
            roltype=roltype_belanghebbende,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.machtiginggever,
            roltoelichting="Persoon waarover bewind gevoerd wordt",
        )

        with self.subTest(MachtigingChoices.eigen):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.eigen},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_eigen)}",
            )

        with self.subTest(MachtigingChoices.gemachtigde):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.gemachtigde},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_gemachtigde)}",
            )

        with self.subTest(MachtigingChoices.machtiginggever):
            response = self.client.get(
                self.url,
                {"rol__machtiging": MachtigingChoices.machtiginggever},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_machtiginggever)}",
            )

    def test_filter_rol_machtiging_loa(self):
        zaaktype = ZaakTypeFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        zaak_low, zaak_high = ZaakFactory.create_batch(2, zaaktype=zaaktype)
        RolFactory.create(
            zaak=zaak_low,
            roltype=roltype,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
                "representee": {
                    "identifier_type": eHerkenningRepresenteeIdentifier.bsn,
                    "identifier": "111222333",
                },
                "mandate": {
                    "role": eHerkenningMandateRole.bewindvoerder,
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ],
                },
            },
        )
        RolFactory.create(
            zaak=zaak_high,
            roltype=roltype,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.high,
                "actingSubject": ACTING_SUBJECT,
                "representee": {
                    "identifier_type": eHerkenningRepresenteeIdentifier.kvk_nummer,
                    "identifier": "12345678",
                },
                "mandate": {
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ],
                },
            },
        )

        with self.subTest(eHerkenningLevelOfAssurance.low_plus):
            response = self.client.get(
                self.url,
                {"rol__machtiging__loa": eHerkenningLevelOfAssurance.low_plus},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(zaak_low)}",
            )

        with self.subTest(eHerkenningLevelOfAssurance.high):
            response = self.client.get(
                self.url,
                {"rol__machtiging__loa": eHerkenningLevelOfAssurance.high},
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)

    def test_filter_rol_nnp_kvk(self):
        zaaktype = ZaakTypeFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol1, rol2, rol3 = RolFactory.create_batch(
            3,
            zaak__zaaktype=zaaktype,
            roltype=roltype,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
        )
        NietNatuurlijkPersoon.objects.create(rol=rol1, kvk_nummer="12345678")
        NietNatuurlijkPersoon.objects.create(rol=rol2, kvk_nummer="11122233")
        NietNatuurlijkPersoon.objects.create(rol=rol3, inn_nnp_id="517439943")

        response = self.client.get(
            self.url,
            {
                "rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer": "12345678"
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"],
            f"http://testserver{reverse(rol1.zaak)}",
        )

    def test_filter_rol_vestiging_kvk(self):
        zaaktype = ZaakTypeFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol1, rol2, rol3 = RolFactory.create_batch(
            3,
            zaak__zaaktype=zaaktype,
            roltype=roltype,
            betrokkene_type=RolTypes.vestiging,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
        )
        Vestiging.objects.create(rol=rol1, kvk_nummer="12345678")
        Vestiging.objects.create(rol=rol2, kvk_nummer="11122233")
        Vestiging.objects.create(rol=rol3, vestigings_nummer="517439943")

        response = self.client.get(
            self.url,
            {"rol__betrokkeneIdentificatie__vestiging__kvkNummer": "12345678"},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"],
            f"http://testserver{reverse(rol1.zaak)}",
        )
