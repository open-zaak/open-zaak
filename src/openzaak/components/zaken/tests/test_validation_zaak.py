# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator, URLValidator
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..constants import AardZaakRelatie, BetalingsIndicatie
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_zaaktype_response


class ZaakValidationTests(SelectieLijstMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    # Needed to pass Django's URLValidator, since the default APIClient domain
    # is not considered a valid URL by Django
    valid_testserver_url = "testserver.nl"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = reverse(cls.zaaktype)

        ServiceFactory.create(api_root="https://example.com/", api_type=APITypes.ztc)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_validate_zaaktype_bad_url(self):
        url = reverse("zaak-list")

        self.requests_mocker.get("https://example.com/zrc/zaken/1234", status_code=404)

        response = self.client.post(
            url,
            {
                "zaaktype": "https://example.com/zrc/zaken/1234",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "zaaktype")
        self.assertEqual(validation_error["code"], "bad-url")
        self.assertEqual(validation_error["name"], "zaaktype")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_validate_zaaktype_invalid_resource(self):
        url = reverse("zaak-list")

        self.requests_mocker.get(
            "https://example.com/", status_code=200, text="<html></html>"
        )

        response = self.client.post(
            url,
            {
                "zaaktype": "https://example.com/",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "zaaktype")
        self.assertEqual(validation_error["code"], "invalid-resource")
        self.assertEqual(validation_error["name"], "zaaktype")

    def test_validate_zaaktype_valid(self, *mocks):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_validate_zaaktype_unpublished(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "zaaktype")
        self.assertEqual(validation_error["code"], "not-published")

    def test_validation_camelcase(self):
        url = reverse("zaak-list")

        response = self.client.post(url, {}, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        bad_casing = get_validation_errors(response, "verantwoordelijke_organisatie")
        self.assertIsNone(bad_casing)

        good_casing = get_validation_errors(response, "verantwoordelijkeOrganisatie")
        self.assertIsNotNone(good_casing)

    def test_validate_communicatiekanaal_invalid_resource(self):
        mock_selectielijst_oas_get(self.requests_mocker)
        communicatiekanaal_url = (
            "https://referentielijsten-api.cloud/api/v1/communicatiekanalen/123"
        )
        self.requests_mocker.get(
            communicatiekanaal_url, status_code=200, json={"something": "wrong"}
        )
        url = reverse("zaak-list")
        body = {"communicatiekanaal": communicatiekanaal_url}

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "communicatiekanaal")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_404")
    def test_validate_communicatiekanaal_bad_url(self):
        url = reverse("zaak-list")
        body = {"communicatiekanaal": "https://someurlthatdoesntexist.com"}

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "communicatiekanaal")
        self.assertEqual(error["code"], URLValidator.code)

    def test_validate_communicatiekanaal_valid(self):
        mock_selectielijst_oas_get(self.requests_mocker)
        self.requests_mocker.get("https://example.com/dummy", json={"dummy": "json"})
        url = reverse("zaak-list")
        body = {"communicatiekanaal": "https://example.com/dummy"}

        with patch("openzaak.utils.validators.obj_has_shape", return_value=True):
            response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "communicatiekanaal")
        self.assertIsNone(error)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_relevante_andere_zaken_invalid(self):
        url = reverse("zaak-list")

        self.requests_mocker.get("https://example.com/andereZaak", status_code=404)

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
                "relevanteAndereZaken": [
                    {
                        "url": "https://example.com/andereZaak",
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ],
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "relevanteAndereZaken.0.url")
        self.assertEqual(validation_error["code"], "bad-url")

    def test_relevante_andere_zaken_valid_zaak_resource(self):
        url = reverse("zaak-list")

        zaak_body = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(url, zaak_body, **ZAAK_WRITE_KWARGS)

        zaak2 = ZaakFactory.create()
        zaak2_url = reverse(zaak2)
        zaak_body.update(
            {
                "relevanteAndereZaken": [
                    {
                        "url": f"http://testserver{zaak2_url}",
                        "aardRelatie": AardZaakRelatie.vervolg,
                    }
                ]
            }
        )

        response = self.client.post(url, zaak_body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_laatste_betaaldatum_betaalindicatie_nvt(self):
        """
        Assert that the field laatsteBetaaldatum may not be set for the NVT
        indication.
        """
        url = reverse("zaak-list")

        # all valid values
        for value in BetalingsIndicatie.values:
            if value == BetalingsIndicatie.nvt:
                continue
            with self.subTest(betalingsindicatie=value):
                response = self.client.post(
                    url,
                    {
                        "zaaktype": f"http://testserver{self.zaaktype_url}",
                        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                        "bronorganisatie": "517439943",
                        "verantwoordelijkeOrganisatie": "517439943",
                        "registratiedatum": "2018-06-11",
                        "startdatum": "2018-06-11",
                        "betalingsindicatie": value,
                        "laatsteBetaaldatum": "2019-01-01T14:03:00Z",
                    },
                    **ZAAK_WRITE_KWARGS,
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # invalid value
        with self.subTest(betalingsindicatie=BetalingsIndicatie.nvt):
            response = self.client.post(
                url,
                {
                    "zaaktype": f"http://testserver{self.zaaktype_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-06-11",
                    "startdatum": "2018-06-11",
                    "betalingsindicatie": BetalingsIndicatie.nvt,
                    "laatsteBetaaldatum": "2019-01-01T14:03:00Z",
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            validation_error = get_validation_errors(response, "laatsteBetaaldatum")
            self.assertEqual(validation_error["code"], "betaling-nvt")

    def test_invalide_product_of_dienst(self):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "productenOfDiensten": ["https://example.com/product/999"],
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "productenOfDiensten")
        self.assertEqual(validation_error["code"], "invalid-products-services")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_404")
    def test_validate_selectielijstklasse_invalid_url(self):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "selectielijstklasse": "https://some-bad-url.com/bla",
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "selectielijstklasse")
        self.assertEqual(validation_error["code"], "bad-url")

    def test_validate_selectielijstklasse_invalid_resource(self):
        mock_selectielijst_oas_get(self.requests_mocker)
        self.requests_mocker.get(
            "https://ztc.com/resultaten/1234", json={"some": "incorrect property"}
        )
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "selectielijstklasse": "https://ztc.com/resultaten/1234",
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "selectielijstklasse")
        self.assertEqual(validation_error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher")
    @patch("vng_api_common.oas.obj_has_shape", return_value=True)
    def test_validate_opdrachtgevende_organisatie_invalid(self, *mocks):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
                "opdrachtgevendeOrganisatie": "000",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "opdrachtgevendeOrganisatie")
        self.assertEqual(validation_error["code"], "invalid-length")
        self.assertEqual(validation_error["name"], "opdrachtgevendeOrganisatie")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher")
    @patch("vng_api_common.oas.obj_has_shape", return_value=True)
    def test_validate_opdrachtgevende_organisatie_valid(self, *mocks):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
                "opdrachtgevendeOrganisatie": "123456782",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ZaakUpdateValidation(SelectieLijstMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_validate_verlenging(self):
        """
        Regression test
        """
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"verlenging": {"reden": "We hebben nog tijd genoeg", "duur": "P0Y1M0D"}},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_validate_opschorting_indicatie_false(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"opschorting": {"indicatie": False, "reden": ""}},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_validate_opschorting_required_fields_partial_update(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url, {"opschorting": {"wrongfield": "bla"}}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for field in ["opschorting.indicatie", "opschorting.reden"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], "required")

    def test_validate_verlenging_required_fields_partial_update(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url, {"verlenging": {"wrongfield": "bla"}}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for field in ["verlenging.reden", "verlenging.duur"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], "required")

    def test_not_allowed_to_change_zaaktype(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)

        response = self.client.patch(
            url, {"zaaktype": f"http://testserver{zaaktype_url}"}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "zaaktype")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)

    def test_not_allowed_to_change_identificatie(self):
        zaak = ZaakFactory.create(identificatie="gibberish")
        url = reverse(zaak)

        response = self.client.patch(
            url, {"identificatie": "new value"}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "identificatie")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)


class DeelZaakValidationTests(SelectieLijstMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_cannot_use_self_as_hoofdzaak(self):
        """
        Hoofdzaak moet een andere zaak zijn dan de deelzaak zelf.
        """
        zaak = ZaakFactory.create()
        detail_url = reverse(zaak)

        response = self.client.patch(
            detail_url, {"hoofdzaak": detail_url}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "hoofdzaak")
        self.assertEqual(error["code"], "self-forbidden")

    def test_cannot_have_multiple_levels(self):
        """
        Deelzaak kan enkel deelzaak zijn van hoofdzaak en niet andere deelzaken.
        """
        url = reverse("zaak-list")
        hoofdzaak = ZaakFactory.create()
        deelzaak = ZaakFactory.create(hoofdzaak=hoofdzaak)
        deelzaak_url = reverse(deelzaak)

        response = self.client.post(
            url, {"hoofdzaak": deelzaak_url}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "hoofdzaak")
        self.assertEqual(error["code"], "deelzaak-als-hoofdzaak")

    @tag("gh-992")
    def test_validate_hoofdzaaktype_deelzaaktypen(self):
        """
        Assert that the zaatkype allowed deelzaaktypen is validated.
        """
        # set up zaaktypen
        hoofdzaaktype = ZaakTypeFactory.create()
        unrelated_zaaktype = ZaakTypeFactory.create(
            catalogus=hoofdzaaktype.catalogus, concept=False
        )
        # set up hoofdzaak
        hoofdzaak = ZaakFactory.create(zaaktype=hoofdzaaktype)

        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{reverse(unrelated_zaaktype)}",
                "hoofdzaak": reverse(hoofdzaak),
                "bronorganisatie": "123456782",
                "verantwoordelijkeOrganisatie": "123456782",
                "startdatum": "1970-01-01",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "hoofdzaak")
        self.assertEqual(error["code"], "invalid-deelzaaktype")

    @tag("gh-992", "external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_validate_hoofdzaaktype_deelzaaktypen_remote_zaaktype(self):
        """
        Assert that the zaaktype allowed deelzaaktypen is validated.
        """
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        # set up zaaktypen
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        hoofdzaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        unrelated_zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/fd2fe097-d033-4a9f-99f4-78abd652e6fd"
        mock_ztc_oas_get(self.requests_mocker)
        self.requests_mocker.get(
            hoofdzaaktype,
            json=get_zaaktype_response(catalogus, hoofdzaaktype, deelzaaktypen=[]),
        )
        self.requests_mocker.get(
            unrelated_zaaktype,
            json=get_zaaktype_response(catalogus, unrelated_zaaktype),
        )
        # set up hoofdzaak
        hoofdzaak = ZaakFactory.create(zaaktype=hoofdzaaktype)
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": unrelated_zaaktype,
                "hoofdzaak": reverse(hoofdzaak),
                "bronorganisatie": "123456782",
                "verantwoordelijkeOrganisatie": "123456782",
                "startdatum": "1970-01-01",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "hoofdzaak")
        self.assertEqual(error["code"], "invalid-deelzaaktype")
