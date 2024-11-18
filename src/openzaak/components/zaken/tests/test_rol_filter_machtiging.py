# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
The tests cover reading, creating and filtering rols with authenticatie_context.
The related US - https://github.com/open-zaak/open-zaak/issues/1733
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolOmschrijving, RolTypes
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..api.filters import MachtigingChoices
from ..api.serializers.authentication_context import (
    DigiDLevelOfAssurance,
    eHerkenningLevelOfAssurance,
    eHerkenningMandateRole,
    eHerkenningRepresenteeIdentifier,
)
from ..constants import IndicatieMachtiging
from ..models import NietNatuurlijkPersoon, Rol, Vestiging
from .factories import RolFactory, ZaakFactory

ACTING_SUBJECT = (
    "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018"
    "@2D8FF1EF10279BC2643F376D89835151"
)


class FilterDigidTests(JWTAuthMixin, APITestCase):
    """
    tests for Rol with Digid authenticatie context
    """

    heeft_alle_autorisaties = True
    url = reverse_lazy(Rol)

    def test_filter_machtiging(self):
        zaak = ZaakFactory.create()
        roltype_initiator = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        roltype_belanghebbende = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )
        rol_eigen = RolFactory.create(
            zaak=zaak,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            roltoelichting="Created zaak",
            authenticatie_context={
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.middle,
            },
        )
        rol_gemachtigde = RolFactory.create(
            zaak=zaak,
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
        rol_machtiginggever = RolFactory.create(
            zaak=zaak,
            roltype=roltype_belanghebbende,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.machtiginggever,
            roltoelichting="Voogd",
        )

        with self.subTest(MachtigingChoices.eigen):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.eigen}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_eigen)}",
            )

        with self.subTest(MachtigingChoices.gemachtigde):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.gemachtigde}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_gemachtigde)}",
            )

        with self.subTest(MachtigingChoices.machtiginggever):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.machtiginggever}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_machtiginggever)}",
            )

    def test_filter_machtiging_loa(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol_loa_middle = RolFactory.create(
            zaak=zaak,
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
            zaak=zaak,
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
                self.url, {"machtiging__loa": DigiDLevelOfAssurance.middle}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_loa_middle)}",
            )

        with self.subTest(DigiDLevelOfAssurance.high):
            response = self.client.get(
                self.url, {"machtiging__loa": DigiDLevelOfAssurance.high}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)

        with self.subTest("invalid"):
            response = self.client.get(self.url, {"machtiging__loa": "invalid"})

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "machtiging__loa")
            self.assertEqual(error["code"], "invalid_choice")


class FilterEHerkenningTests(JWTAuthMixin, APITestCase):
    """
    tests for Rol with eHerkenning authenticatie context
    """

    heeft_alle_autorisaties = True
    url = reverse_lazy(Rol)

    def test_filter_machtiging(self):
        zaak = ZaakFactory.create()
        roltype_initiator = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        roltype_belanghebbende = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )
        rol_eigen = RolFactory.create(
            zaak=zaak,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "acting_subject": ACTING_SUBJECT,
            },
        )
        rol_gemachtigde = RolFactory.create(
            zaak=zaak,
            roltype=roltype_initiator,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "acting_subject": ACTING_SUBJECT,
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
        rol_machtiginggever = RolFactory.create(
            zaak=zaak,
            roltype=roltype_belanghebbende,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.machtiginggever,
            roltoelichting="Persoon waarover bewind gevoerd wordt",
        )

        with self.subTest(MachtigingChoices.eigen):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.eigen}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_eigen)}",
            )

        with self.subTest(MachtigingChoices.gemachtigde):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.gemachtigde}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_gemachtigde)}",
            )

        with self.subTest(MachtigingChoices.machtiginggever):
            response = self.client.get(
                self.url, {"machtiging": MachtigingChoices.machtiginggever}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_machtiginggever)}",
            )

    def test_filter_machtiging_loa(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol_low = RolFactory.create(
            zaak=zaak,
            roltype=roltype,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "acting_subject": ACTING_SUBJECT,
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
            zaak=zaak,
            roltype=roltype,
            betrokkene_type=RolTypes.vestiging,
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
            roltoelichting="Created zaak",
            contactpersoon_rol_naam="acting subject name",
            authenticatie_context={
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.high,
                "acting_subject": ACTING_SUBJECT,
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
                self.url, {"machtiging__loa": eHerkenningLevelOfAssurance.low_plus}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(
                response.json()["results"][0]["url"],
                f"http://testserver{reverse(rol_low)}",
            )

        with self.subTest(eHerkenningLevelOfAssurance.high):
            response = self.client.get(
                self.url, {"machtiging__loa": eHerkenningLevelOfAssurance.high}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["count"], 2)

        with self.subTest("invalid"):
            response = self.client.get(self.url, {"machtiging__loa": "invalid"})

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "machtiging__loa")
            self.assertEqual(error["code"], "invalid_choice")

    def test_filter_nnp_kvk(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol1, rol2, rol3 = RolFactory.create_batch(
            3,
            zaak=zaak,
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
            {"betrokkeneIdentificatie__nietNatuurlijkPersoon__kvkNummer": "12345678"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"],
            f"http://testserver{reverse(rol1)}",
        )

    def test_filter_vestiging_kvk(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        rol1, rol2, rol3 = RolFactory.create_batch(
            3,
            zaak=zaak,
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
            {"betrokkeneIdentificatie__vestiging__kvkNummer": "12345678"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["url"],
            f"http://testserver{reverse(rol1)}",
        )
