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

from ..api.serializers.authentication_context import (
    DigiDLevelOfAssurance,
    eHerkenningLevelOfAssurance,
    eHerkenningRepresenteeIdentifier,
)
from ..constants import IndicatieMachtiging
from ..models import Rol
from .factories import ZaakFactory
from .utils import AuthContextAssertMixin

ACTING_SUBJECT = (
    "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018"
    "@2D8FF1EF10279BC2643F376D89835151"
)


class AuthContextDigidTests(AuthContextAssertMixin, JWTAuthMixin, APITestCase):
    """
    tests for Rol with Digid authenticatie context
    """

    heeft_alle_autorisaties = True
    url = reverse_lazy(Rol)

    def test_create_digid_without_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {"inpBsn": "123456782"},
            "authenticatieContext": {
                "source": "digid",
                "levelOfAssurance": DigiDLevelOfAssurance.middle,
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.natuurlijk_persoon)
        self.assertEqual(rol.indicatie_machtiging, "")
        self.assertEqual(
            rol.authenticatie_context,
            {"source": "digid", "level_of_assurance": DigiDLevelOfAssurance.middle},
        )
        self.assertEqual(rol.natuurlijkpersoon.inp_bsn, "123456782")

        # check that we can construct auth context valid against the auth context JSON schema
        context = rol.construct_auth_context_data()
        self.assertValidContext(context)

    def test_create_digid_with_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "indicatieMachtiging": IndicatieMachtiging.gemachtigde,
            "betrokkeneIdentificatie": {"inpBsn": "123456782"},
            "authenticatieContext": {
                "source": "digid",
                "levelOfAssurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifierType": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.natuurlijk_persoon)
        self.assertEqual(rol.indicatie_machtiging, IndicatieMachtiging.gemachtigde)
        self.assertEqual(
            rol.authenticatie_context,
            {
                "source": "digid",
                "level_of_assurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifier_type": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        )
        self.assertEqual(rol.natuurlijkpersoon.inp_bsn, "123456782")

        # check that we can construct auth context valid against the auth context JSON schema
        context = rol.construct_auth_context_data()
        print("context=", context)
        self.assertValidContext(context)

    def test_create_digid_with_mandate_incorrect_indicatie_machtigen(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {"inpBsn": "123456782"},
            "authenticatieContext": {
                "source": "digid",
                "levelOfAssurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifierType": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "indicatie-machtiging-invalid")

    def test_create_digid_with_mandate_empty_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {"inpBsn": "123456782"},
            "authenticatieContext": {
                "source": "digid",
                "levelOfAssurance": DigiDLevelOfAssurance.middle,
                "representee": {"identifierType": "bsn", "identifier": "111222333"},
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "authenticatieContext.mandate")
        self.assertEqual(error["code"], "required")

    def test_create_digid_with_mandate_incorrect_source(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {"inpBsn": "123456782"},
            "authenticatieContext": {
                "levelOfAssurance": DigiDLevelOfAssurance.middle,
            },
        }

        for source in ["", "eherkenning", "invalid"]:
            with self.subTest(source):
                data["authenticatieContext"]["source"] = source

                response = self.client.post(self.url, data)

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )

                error = get_validation_errors(response, "authenticatieContext.source")
                self.assertEqual(error["code"], "invalid_choice")


class AuthContextEHerkenningTests(AuthContextAssertMixin, JWTAuthMixin, APITestCase):
    """
    tests for Rol with eHerkenning without mandate:
    """

    maxDiff = None
    heeft_alle_autorisaties = True
    url = reverse_lazy(Rol)

    def test_create_eherkenning_nnp_without_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "contactpersoonRol": {"naam": "acting subject name"},
            "betrokkeneIdentificatie": {"kvkNummer": "12345678"},
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.niet_natuurlijk_persoon)
        self.assertEqual(rol.contactpersoon_rol_naam, "acting subject name")
        self.assertEqual(rol.indicatie_machtiging, "")
        self.assertEqual(
            rol.authenticatie_context,
            {
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "acting_subject": ACTING_SUBJECT,
            },
        )
        self.assertEqual(rol.nietnatuurlijkpersoon.kvk_nummer, "12345678")

        # check that we can construct auth context valid against the auth context JSON schema
        context = rol.construct_auth_context_data()
        self.assertValidContext(context)

    def test_create_eherkenning_vestiging_without_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.vestiging,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "contactpersoonRol": {"naam": "acting subject name"},
            "betrokkeneIdentificatie": {
                "kvkNummer": "12345678",
                "vestigingsNummer": "123456789012",
            },
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.vestiging)
        self.assertEqual(rol.contactpersoon_rol_naam, "acting subject name")
        self.assertEqual(rol.indicatie_machtiging, "")
        self.assertEqual(
            rol.authenticatie_context,
            {
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "acting_subject": ACTING_SUBJECT,
            },
        )
        self.assertEqual(rol.vestiging.kvk_nummer, "12345678")
        self.assertEqual(rol.vestiging.vestigings_nummer, "123456789012")

        # check that we can construct auth context valid against the auth context JSON schema
        context = rol.construct_auth_context_data()
        self.assertValidContext(context)

    def test_create_eherkenning_vestiging_with_mandate_np(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.vestiging,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "contactpersoonRol": {"naam": "acting subject name"},
            "indicatieMachtiging": IndicatieMachtiging.gemachtigde,
            "betrokkeneIdentificatie": {
                "kvkNummer": "12345678",
                "vestigingsNummer": "123456789012",
            },
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifierType": eHerkenningRepresenteeIdentifier.bsn,
                    "identifier": "111222333",
                },
                "actingSubject": ACTING_SUBJECT,
                "mandate": {
                    "role": "bewindvoerder",
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ],
                },
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.vestiging)
        self.assertEqual(rol.contactpersoon_rol_naam, "acting subject name")
        self.assertEqual(rol.indicatie_machtiging, IndicatieMachtiging.gemachtigde)
        self.assertEqual(
            rol.authenticatie_context,
            {
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifier_type": eHerkenningRepresenteeIdentifier.bsn,
                    "identifier": "111222333",
                },
                "acting_subject": ACTING_SUBJECT,
                "mandate": {
                    "role": "bewindvoerder",
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ],
                },
            },
        )
        self.assertEqual(rol.vestiging.kvk_nummer, "12345678")
        self.assertEqual(rol.vestiging.vestigings_nummer, "123456789012")

        context = rol.construct_auth_context_data()
        self.assertValidContext(context)

    def test_create_eherkenning_nnp_with_mandate_company(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "indicatieMachtiging": IndicatieMachtiging.gemachtigde,
            "contactpersoonRol": {"naam": "acting subject name"},
            "betrokkeneIdentificatie": {
                "kvkNummer": "12345678",
            },
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifierType": eHerkenningRepresenteeIdentifier.kvk_nummer,
                    "identifier": "99998888",
                },
                "actingSubject": ACTING_SUBJECT,
                "mandate": {
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ]
                },
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rol = Rol.objects.get()

        self.assertEqual(rol.omschrijving_generiek, RolOmschrijving.initiator)
        self.assertEqual(rol.betrokkene_type, RolTypes.niet_natuurlijk_persoon)
        self.assertEqual(rol.contactpersoon_rol_naam, "acting subject name")
        self.assertEqual(rol.indicatie_machtiging, IndicatieMachtiging.gemachtigde)
        self.assertEqual(
            rol.authenticatie_context,
            {
                "source": "eherkenning",
                "level_of_assurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifier_type": eHerkenningRepresenteeIdentifier.kvk_nummer,
                    "identifier": "99998888",
                },
                "acting_subject": ACTING_SUBJECT,
                "mandate": {
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ]
                },
            },
        )
        self.assertEqual(rol.nietnatuurlijkpersoon.kvk_nummer, "12345678")

        context = rol.construct_auth_context_data()
        self.assertValidContext(context)

    def test_create_eherkenning_with_mandate_empty_mandate(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "contactpersoonRol": {"naam": "acting subject name"},
            "indicatieMachtiging": IndicatieMachtiging.gemachtigde,
            "betrokkeneIdentificatie": {"kvkNummer": "12345678"},
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifierType": eHerkenningRepresenteeIdentifier.bsn,
                    "identifier": "111222333",
                },
                "actingSubject": ACTING_SUBJECT,
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "authenticatieContext.mandate")
        self.assertEqual(error["code"], "required")

    def test_create_eherkenning_with_mandate_incorrect_indicatie_machtigen(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.vestiging,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "contactpersoonRol": {"naam": "acting subject name"},
            "betrokkeneIdentificatie": {
                "kvkNummer": "12345678",
                "vestigingsNummer": "123456789012",
            },
            "authenticatieContext": {
                "source": "eherkenning",
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "representee": {
                    "identifierType": eHerkenningRepresenteeIdentifier.kvk_nummer,
                    "identifier": "99998888",
                },
                "actingSubject": ACTING_SUBJECT,
                "mandate": {
                    "services": [
                        {
                            "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                            "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc",
                        }
                    ]
                },
            },
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "indicatie-machtiging-invalid")

    def test_create_eherkenning_nnp_with_mandate_incorrect_source(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {"kvkNummer": "12345678"},
            "contactpersoonRol": {"naam": "acting subject name"},
            "authenticatieContext": {
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
            },
        }

        for source in ["", "digid", "invalid"]:
            with self.subTest(source):
                data["authenticatieContext"]["source"] = source

                response = self.client.post(self.url, data)

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )

                error = get_validation_errors(response, "authenticatieContext.source")
                self.assertEqual(error["code"], "invalid_choice")

    def test_create_eherkenning_vestiging_with_mandate_incorrect_source(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.initiator
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkeneType": RolTypes.vestiging,
            "roltype": f"http://testserver{reverse(roltype)}",
            "roltoelichting": "Created zaak",
            "betrokkeneIdentificatie": {
                "kvkNummer": "12345678",
                "vestigingsNummer": "123456789012",
            },
            "contactpersoonRol": {"naam": "acting subject name"},
            "authenticatieContext": {
                "levelOfAssurance": eHerkenningLevelOfAssurance.low_plus,
                "actingSubject": ACTING_SUBJECT,
            },
        }

        for source in ["", "digid", "invalid"]:
            with self.subTest(source):
                data["authenticatieContext"]["source"] = source

                response = self.client.post(self.url, data)

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )

                error = get_validation_errors(response, "authenticatieContext.source")
                self.assertEqual(error["code"], "invalid_choice")
