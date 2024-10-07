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
)
from ..constants import IndicatieMachtiging
from ..models import Rol
from .factories import ZaakFactory


class AuthContextDigidTests(JWTAuthMixin, APITestCase):
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
                "representee": {"identifierType": "bsn", "identifier": "111222333"},
                "mandate": {
                    "services": [{"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}]
                },
            },
        )
        self.assertEqual(rol.natuurlijkpersoon.inp_bsn, "123456782")

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
