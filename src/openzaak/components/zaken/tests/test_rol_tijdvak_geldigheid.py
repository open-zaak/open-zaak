# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from datetime import date

from django.test import override_settings, tag

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolOmschrijving, RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import RolTypeFactory
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import Rol
from .factories import RolFactory, ZaakFactory
from .utils import get_operation_url, get_roltype_response, get_zaaktype_response

BETROKKENE = (
    "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


@freeze_time("2025-01-01T12:00:00")
class RolTijdvakGeldigheidTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    list_url = get_operation_url("rol_create")

    def test_create_rol_with_tijdvak_geldigheid(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "foo",
            "tijdvakGeldigheid": {
                "beginGeldigheid": "2025-01-01",
                "eindGeldigheid": "2025-02-01",
            },
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()

        self.assertEqual(rol.tijdvak_geldigheid_begin_geldigheid, date(2025, 1, 1))
        self.assertEqual(rol.tijdvak_geldigheid_eind_geldigheid, date(2025, 2, 1))

    def test_create_rol_with_tijdvak_geldigheid_without_eind_geldigheid(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "foo",
            "tijdvakGeldigheid": {"beginGeldigheid": "2025-01-01"},
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()

        self.assertEqual(rol.tijdvak_geldigheid_begin_geldigheid, date(2025, 1, 1))
        self.assertEqual(rol.tijdvak_geldigheid_eind_geldigheid, None)

    def test_create_rol_with_tijdvak_geldigheid_eind_cannot_be_before_begin(self):
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "foo",
            "tijdvakGeldigheid": {
                "beginGeldigheid": "2025-01-01",
                "eindGeldigheid": "2024-01-01",
            },
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Rol.objects.count(), 0)

        validation_error = get_validation_errors(
            response, "tijdvakGeldigheid.eindGeldigheid"
        )

        self.assertEqual(
            validation_error["code"], "eind-geldigheid-before-begin-geldigheid"
        )

    def test_update_rol_with_tijdvak_geldigheid_eind_cannot_be_before_begin(self):
        rol = RolFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=rol.zaak.uuid)
        roltype_url = reverse(rol.roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "foo",
            "tijdvakGeldigheid": {
                "beginGeldigheid": "2025-01-01",
                "eindGeldigheid": "2024-01-01",
            },
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(
            response, "tijdvakGeldigheid.eindGeldigheid"
        )

        self.assertEqual(
            validation_error["code"], "eind-geldigheid-before-begin-geldigheid"
        )

    def test_create_rol_only_one_medewerker_behandelaar_allowed_during_validity_period(
        self,
    ):
        """
        It is only allowed to have one `medewerker` (betrokkeneType) as
        `behandelaar` (roltype) during a validity period
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        behandelaar_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        RolFactory.create(
            zaak=zaak,
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.medewerker,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Other zaak, should not affect validation
        RolFactory.create(
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.medewerker,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )
        roltype_url = reverse(behandelaar_roltype)

        # Overlap
        for begin, end in [
            ("2025-01-01", "2025-02-01"),
            ("2025-01-01", None),
            ("2025-01-15", "2025-02-15"),
            ("2024-06-01", "2025-01-02"),
            ("2024-06-01", "2025-01-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.medewerker,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                validation_error = get_validation_errors(response, "nonFieldErrors")
                assert validation_error
                self.assertEqual(
                    validation_error["code"], "behandelaar-tijdvak-geldigheid-overlap"
                )

        # No overlap
        for begin, end in [
            # TODO verify if this is correct behavior
            # ("2024-06-01", "2025-01-01"),
            # ("2024-02-01", "2025-03-01"),
            ("2025-02-02", "2025-03-01"),
            ("2026-06-01", "2026-07-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.medewerker,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_rol_only_one_medewerker_behandelaar_allowed_during_validity_period(
        self,
    ):
        """
        It is only allowed to have one `medewerker` (betrokkeneType) as
        `behandelaar` (roltype) during a validity period
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        behandelaar_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        RolFactory.create(
            zaak=zaak,
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.medewerker,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Other zaak, should not affect validation
        RolFactory.create(
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.medewerker,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )
        roltype_url = reverse(behandelaar_roltype)

        rol_to_update = RolFactory(zaak=zaak, roltype=behandelaar_roltype)
        rol_url = reverse(rol_to_update)

        # Overlap
        for begin, end in [
            ("2025-01-01", "2025-02-01"),
            ("2025-01-01", None),
            ("2025-01-15", "2025-02-15"),
            ("2024-06-01", "2025-01-02"),
            ("2024-06-01", "2025-01-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.medewerker,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.put(rol_url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                validation_error = get_validation_errors(response, "nonFieldErrors")

                assert validation_error
                self.assertEqual(
                    validation_error["code"], "behandelaar-tijdvak-geldigheid-overlap"
                )

        # No overlap
        for begin, end in [
            # TODO verify if this is correct behavior
            # ("2024-06-01", "2025-01-01"),
            # ("2024-02-01", "2025-03-01"),
            ("2025-02-02", "2025-03-01"),
            ("2026-06-01", "2026-07-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.medewerker,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.put(rol_url, data)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_rol_only_one_organisatorische_eenheid_behandelaar_allowed_during_validity_period(
        self,
    ):
        """
        It is only allowed to have one `organisatorische_eenheid` (betrokkeneType) as
        `behandelaar` (roltype) during a validity period
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        behandelaar_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        RolFactory.create(
            zaak=zaak,
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Other zaak, should not affect validation
        RolFactory.create(
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )
        roltype_url = reverse(behandelaar_roltype)

        # Overlap
        for begin, end in [
            ("2025-01-01", "2025-02-01"),
            ("2025-01-01", None),
            ("2025-01-15", "2025-02-15"),
            ("2024-06-01", "2025-01-02"),
            ("2024-06-01", "2025-01-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                validation_error = get_validation_errors(response, "nonFieldErrors")
                assert validation_error
                self.assertEqual(
                    validation_error["code"], "behandelaar-tijdvak-geldigheid-overlap"
                )

        # No overlap
        for begin, end in [
            # TODO verify if this is correct behavior
            # ("2024-06-01", "2025-01-01"),
            # ("2024-02-01", "2025-03-01"),
            ("2025-02-02", "2025-03-01"),
            ("2026-06-01", "2026-07-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_rol_only_one_organisatorische_eenheid_behandelaar_allowed_during_validity_period(
        self,
    ):
        """
        It is only allowed to have one `organisatorische_eenheid` (betrokkeneType) as
        `behandelaar` (roltype) during a validity period
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        behandelaar_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        RolFactory.create(
            zaak=zaak,
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Other zaak, should not affect validation
        RolFactory.create(
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )
        roltype_url = reverse(behandelaar_roltype)

        rol_to_update = RolFactory(zaak=zaak, roltype=behandelaar_roltype)
        rol_url = reverse(rol_to_update)

        # Overlap
        for begin, end in [
            ("2025-01-01", "2025-02-01"),
            ("2025-01-01", None),
            ("2025-01-15", "2025-02-15"),
            ("2024-06-01", "2025-01-02"),
            ("2024-06-01", "2025-01-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.put(rol_url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                validation_error = get_validation_errors(response, "nonFieldErrors")

                assert validation_error
                self.assertEqual(
                    validation_error["code"], "behandelaar-tijdvak-geldigheid-overlap"
                )

        # No overlap
        for begin, end in [
            # TODO verify if this is correct behavior
            # ("2024-06-01", "2025-01-01"),
            # ("2024-02-01", "2025-03-01"),
            ("2025-02-02", "2025-03-01"),
            ("2026-06-01", "2026-07-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": f"http://testserver{roltype_url}",
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.put(rol_url, data)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_rol_only_validity_period_validation_does_not_apply_in_some_cases(
        self,
    ):
        """
        tijdvakGeldigheid validation should not apply if:

        - no tijdvakGeldigheid is specified for the created Rol
        - if betrokkeneType is not the same as other `behandelaar` within tijdvakGeldigheid
        - if roltype.omschrijving_generiek is not `behandelaar`
        """
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        behandelaar_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        adviseur_roltype = RolTypeFactory.create(
            zaaktype=zaak.zaaktype, omschrijving_generiek=RolOmschrijving.adviseur
        )
        RolFactory.create(
            zaak=zaak,
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Other zaak, should not affect validation
        RolFactory.create(
            roltype=behandelaar_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )
        roltype_url = reverse(behandelaar_roltype)
        adviseur_roltype_url = reverse(adviseur_roltype)

        with self.subTest("no tijdvakGeldigheid specified"):
            data = {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.organisatorische_eenheid,
                "roltype": f"http://testserver{roltype_url}",
                "roltoelichting": "foo",
                "tijdvakGeldigheid": None,
            }

            response = self.client.post(self.list_url, data)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("betrokkeneType is different"):
            data = {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.medewerker,
                "roltype": f"http://testserver{roltype_url}",
                "roltoelichting": "foo",
                "tijdvakGeldigheid": {
                    "beginGeldigheid": "2025-01-01",
                    "eindGeldigheid": "2025-02-01",
                },
            }

            response = self.client.post(self.list_url, data)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("not behandelaar roltype"):
            data = {
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkene_type": RolTypes.organisatorische_eenheid,
                "roltype": f"http://testserver{adviseur_roltype_url}",
                "roltoelichting": "foo",
                "tijdvakGeldigheid": {
                    "beginGeldigheid": "2025-01-01",
                    "eindGeldigheid": "2025-02-01",
                },
            }

            response = self.client.post(self.list_url, data)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    @requests_mock.Mocker()
    def test_create_rol_only_one_organisatorische_eenheid_behandelaar_allowed_during_validity_period_external(
        self, m
    ):
        """
        It is only allowed to have one `organisatorische_eenheid` (betrokkeneType) as
        `behandelaar` (roltype) during a validity period
        """
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        external_roltype = "https://externe.catalogus.nl/api/v1/roltypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        irrelevant_roltype = "https://externe.catalogus.nl/api/v1/roltypen/41c2b1fa-7b2d-4bd8-87b6-5c3ddb5ef226"

        mock_ztc_oas_get(m)
        m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
        m.get(
            external_roltype,
            json=get_roltype_response(
                external_roltype,
                zaaktype,
                omschrijving_generiek=RolOmschrijving.behandelaar,
            ),
        )
        m.get(
            irrelevant_roltype,
            json=get_roltype_response(
                irrelevant_roltype,
                zaaktype,
                omschrijving_generiek=RolOmschrijving.adviseur,
            ),
        )

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        RolFactory.create(
            zaak=zaak,
            roltype=external_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2025, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2025, 2, 1),
        )
        # Not `behandelaar`, should not affect validation
        RolFactory.create(
            roltype=irrelevant_roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            tijdvak_geldigheid_begin_geldigheid=date(2010, 1, 1),
            tijdvak_geldigheid_eind_geldigheid=date(2030, 2, 1),
        )

        # Overlap
        for begin, end in [
            ("2025-01-01", "2025-02-01"),
            ("2025-01-01", None),
            ("2025-01-15", "2025-02-15"),
            ("2024-06-01", "2025-01-02"),
            ("2024-06-01", "2025-01-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": external_roltype,
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                validation_error = get_validation_errors(response, "nonFieldErrors")
                assert validation_error
                self.assertEqual(
                    validation_error["code"], "behandelaar-tijdvak-geldigheid-overlap"
                )

        # No overlap
        for begin, end in [
            # TODO verify if this is correct behavior
            # ("2024-06-01", "2025-01-01"),
            # ("2024-02-01", "2025-03-01"),
            ("2025-02-02", "2025-03-01"),
            ("2026-06-01", "2026-07-01"),
        ]:
            with self.subTest(begin=begin, end=end):
                tijdvak = {"beginGeldigheid": begin}
                if end:
                    tijdvak["eindGeldigheid"] = end

                data = {
                    "zaak": f"http://testserver{zaak_url}",
                    "betrokkene": BETROKKENE,
                    "betrokkene_type": RolTypes.organisatorische_eenheid,
                    "roltype": external_roltype,
                    "roltoelichting": "foo",
                    "tijdvakGeldigheid": tijdvak,
                }

                response = self.client.post(self.list_url, data)

                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
