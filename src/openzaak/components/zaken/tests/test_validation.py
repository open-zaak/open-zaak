# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import datetime
from unittest.mock import patch

from django.test import override_settings, tag
from django.utils.timezone import make_aware

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator, URLValidator
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.tests.utils import JWTAuthMixin, get_eio_response, mock_ztc_oas_get

from ..constants import AardZaakRelatie, BetalingsIndicatie
from ..models import KlantContact, Resultaat, ZaakInformatieObject, ZaakObject
from .factories import (
    KlantContactFactory,
    ResultaatFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_zaaktype_response, isodatetime


class ZaakValidationTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    # Needed to pass Django's URLValidator, since the default APIClient domain
    # is not considered a valid URL by Django
    valid_testserver_url = "testserver.nl"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_root="https://example.com/", api_type=APITypes.ztc)
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = reverse(cls.zaaktype)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_validate_zaaktype_bad_url(self):
        url = reverse("zaak-list")

        with requests_mock.Mocker() as m:
            m.get("https://example.com/zrc/zaken/1234", status_code=404)

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

        with requests_mock.Mocker() as m:
            m.get("https://example.com/", status_code=200, text="<html></html>")

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

    @requests_mock.Mocker()
    def test_validate_communicatiekanaal_invalid_resource(self, m):
        mock_selectielijst_oas_get(m)
        communicatiekanaal_url = (
            "https://referentielijsten-api.cloud/api/v1/communicatiekanalen/123"
        )
        m.get(communicatiekanaal_url, status_code=200, json={"something": "wrong"})
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

    @requests_mock.Mocker()
    def test_validate_communicatiekanaal_valid(self, m):
        mock_selectielijst_oas_get(m)
        m.get("https://example.com/dummy", json={"dummy": "json"})
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

        response = self.client.post(
            url,
            {
                "zaaktype": "https://example.com/foo/bar",
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
                "zaaktype": "https://example.com/foo/bar",
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

    @requests_mock.Mocker()
    def test_validate_selectielijstklasse_invalid_resource(self, m):
        mock_selectielijst_oas_get(m)
        m.get("https://ztc.com/resultaten/1234", json={"some": "incorrect property"})
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_validate_opdrachtgevende_organisatie_invalid(self, *mocks):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": "https://example.com/foo/bar",
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
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
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


class ZaakUpdateValidation(JWTAuthMixin, APITestCase):
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


class DeelZaakValidationTests(JWTAuthMixin, APITestCase):

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
    def test_validate_hoofdzaaktype_deelzaaktypen_remote_zaaktype(self):
        """
        Assert that the zaatkype allowed deelzaaktypen is validated.
        """
        # set up zaaktypen
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        hoofdzaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        unrelated_zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/fd2fe097-d033-4a9f-99f4-78abd652e6fd"
        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(
                hoofdzaaktype,
                json=get_zaaktype_response(catalogus, hoofdzaaktype, deelzaaktypen=[]),
            )
            m.get(
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


class ZaakInformatieObjectValidationTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_informatieobject_invalid(self):
        Service.objects.create(api_root="https://drc.nl/", api_type=APITypes.drc)
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url, {"zaak": zaak_url, "informatieobject": "https://drc.nl/api/v1"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "informatieobject")
        self.assertEqual(validation_error["code"], "bad-url")
        self.assertEqual(validation_error["name"], "informatieobject")

    def test_informatieobject_no_zaaktype_informatieobjecttype_relation(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            validation_error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_informatieobject_create(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_informatieobject_fails(self):
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)

        zio = ZaakInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype=io.informatieobjecttype
        )
        zio_url = reverse(zio)

        response = self.client.patch(
            zio_url, {"informatieobject": f"http://testserver{io_url}"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "informatieobject")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)


class FilterValidationTests(JWTAuthMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_zaak_invalid_filters(self):
        url = reverse("zaak-list")

        invalid_filters = {"zaaktype": "123", "bronorganisatie": "123", "foo": "bar"}

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value}, **ZAAK_WRITE_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rol_invalid_filters(self):
        url = reverse("rol-list")

        invalid_filters = {
            "zaak": "123",  # must be a url
            "betrokkene": "123",  # must be a url
            "betrokkeneType": "not-a-valid-choice",  # must be a pre-defined choice
            "rolomschrijving": "not-a-valid-choice",  # must be a pre-defined choice
            "foo": "bar",
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_invalid_filters(self):
        url = reverse("status-list")

        invalid_filters = {
            "zaak": "123",  # must be a url
            "statustype": "123",  # must be a url
            "foo": "bar",
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_klantcontact_unknown_query_params(self):
        KlantContactFactory.create_batch(2)
        url = reverse(KlantContact)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_resultaat_unknown_query_params(self):
        ResultaatFactory.create_batch(2)
        url = reverse(Resultaat)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_zaakinformatieobject_unknown_query_params(self):
        ZaakInformatieObjectFactory.create_batch(2)
        url = reverse(ZaakInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_validate_zaakobject_unknown_query_params(self):
        ZaakObjectFactory.create_batch(2)
        url = reverse(ZaakObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class StatusValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_root="https://external.nl/", api_type=APITypes.ztc)
        cls.zaaktype = ZaakTypeFactory.create()
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_end = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.zaaktype_url = reverse(cls.zaaktype)
        cls.statustype_url = reverse(cls.statustype)
        cls.statustype_end_url = reverse(cls.statustype_end)

    def test_not_allowed_to_change_statustype(self):
        _status = StatusFactory.create()
        url = reverse(_status)

        response = self.client.patch(
            url, {"statustype": "https://ander.statustype.nl/foo/bar"}
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_statustype_valid_resource(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_statustype_bad_url(self):
        Service.objects.create(
            api_root="https://ander.statustype.nl/", api_type=APITypes.ztc
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": "https://ander.statustype.nl/foo/bar",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "bad-url")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_statustype_invalid_resource(self):
        Service.objects.create(api_root="https://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        with requests_mock.Mocker() as m:
            m.get("https://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                list_url,
                {
                    "zaak": zaak_url,
                    "statustype": "https://example.com/",
                    "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "statustype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_statustype_zaaktype_mismatch(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "zaaktype-mismatch")

    @freeze_time("2019-07-22T12:00:00")
    def test_status_datum_status_gezet_cannot_be_in_future(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": self.statustype_url,
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "datumStatusGezet")
        self.assertEqual(validation_error["code"], "date-in-future")

    def test_status_with_informatieobject_lock(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(canonical__lock=uuid.uuid4().hex)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io.canonical)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "informatieobject-locked")

    def test_status_with_informatieobject_indicatie_gebruiksrecht_null(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(indicatie_gebruiksrecht=None)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io.canonical)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "indicatiegebruiksrecht-unset")

    def test_unique_date_status_set_zaak_combination(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        timestamp = make_aware(datetime(2021, 8, 30, 10, 0, 0))
        StatusFactory.create(zaak=zaak, datum_status_gezet=timestamp)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": timestamp.isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResultaatValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_not_allowed_to_change_resultaattype(self):
        resultaat = ResultaatFactory.create()
        url = reverse(resultaat)
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(
            url, {"resultaattype": f"http://testserver{resultaattype_url}"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "resultaattype")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_resultaattype_bad_url(self):
        Service.objects.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )
        zaak = ZaakFactory.create()
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        list_url = reverse("resultaat-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "resultaattype": "https://externe.catalogus.nl/api/v1/foo/bar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "resultaattype")
        self.assertEqual(validation_error["code"], "bad-url")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_resultaattype_invalid_resource(self):
        Service.objects.create(api_root="https://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory.create()
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        list_url = reverse("resultaat-list")

        with requests_mock.Mocker() as m:
            m.get("https://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                list_url, {"zaak": zaak_url, "resultaattype": "https://example.com/"}
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "resultaattype")
        self.assertEqual(validation_error["code"], "invalid-resource")

    def test_resultaattype_incorrect_zaaktype(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        list_url = reverse("resultaat-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "resultaattype": f"http://testserver{resultaattype_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaaktype-mismatch")


class KlantContactValidationTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2019-07-22T12:00:00")
    def test_klantcontact_datumtijd_not_in_future(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        list_url = reverse("klantcontact-list")

        response = self.client.post(
            list_url,
            {"zaak": zaak_url, "datumtijd": "2019-07-22T13:00:00", "kanaal": "test"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "datumtijd")
        self.assertEqual(validation_error["code"], "date-in-future")

    def test_klantcontact_invalid_zaak(self):
        list_url = reverse("klantcontact-list")

        response = self.client.post(
            list_url,
            {
                "zaak": "some-wrong-value",
                "datumtijd": "2019-07-22T12:00:00",
                "kanaal": "test",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "zaak")
        self.assertEqual(validation_error["code"], "object-does-not-exist")


class ZaakEigenschapValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create_eigenschap(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        eigenschap = EigenschapFactory.create(zaaktype=zaak.zaaktype)
        eigenschap_url = reverse(eigenschap)
        list_url = reverse("zaakeigenschap-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "eigenschap": f"http://testserver{eigenschap_url}",
                "waarde": "test",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_eigenschap_invalid_url(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        list_url = reverse("zaakeigenschap-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(
            list_url, {"zaak": zaak_url, "eigenschap": "bla", "waarde": "test"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "eigenschap")
        self.assertEqual(validation_error["code"], "bad-url")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_eigenschap_invalid_resource(self):
        Service.objects.create(api_root="http://example.com/", api_type=APITypes.ztc)
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        list_url = reverse("zaakeigenschap-list", kwargs={"zaak_uuid": zaak.uuid})

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                list_url,
                {
                    "zaak": zaak_url,
                    "eigenschap": "http://example.com/",
                    "waarde": "test",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "eigenschap")
        self.assertEqual(validation_error["code"], "invalid-resource")


class ZaakObjectValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @requests_mock.Mocker()
    def test_create_zaakobject(self, m):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        list_url = reverse("zaakobject-list")
        m.get(
            "http://some-api.com/objecten/1234",
            json={"url": "http://some-api.com/objecten/1234"},
        )

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "object": "http://some-api.com/objecten/1234",
                "objectType": "adres",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_404")
    def test_create_zaakobject_invalid_url(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        list_url = reverse("zaakobject-list")
        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "object": "http://some-api.com/objecten/1234",
                "objectType": "adres",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "object")
        self.assertEqual(validation_error["code"], "bad-url")


@tag("external-urls")
@requests_mock.Mocker()
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    """
    Test validation with remote documents involved.
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            api_root="https://external.catalogus.nl/", api_type=APITypes.ztc
        )
        cls.zaaktype = ZaakTypeFactory.create()
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_end = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.zaaktype_url = reverse(cls.zaaktype)
        cls.statustype_url = reverse(cls.statustype)
        cls.statustype_end_url = reverse(cls.statustype_end)

    def test_eindstatus_with_informatieobject_unlocked(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(
                REMOTE_DOCUMENT, locked=False, indicatieGebruiksrecht=False,
            ),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_eindstatus_with_informatieobject_lock(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT, json=get_eio_response(REMOTE_DOCUMENT, locked=True),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "informatieobject-locked")

    def test_status_with_informatieobject_indicatie_gebruiksrecht_null(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(REMOTE_DOCUMENT, indicatieGebruiksrecht=None),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "indicatiegebruiksrecht-unset")
