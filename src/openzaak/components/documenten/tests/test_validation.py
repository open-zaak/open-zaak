# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from base64 import b64encode
from copy import deepcopy

from django.contrib.sites.models import Site
from django.test import override_settings, tag
from django.utils.translation import gettext_lazy as _

import requests_mock
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_LOCK,
)
from ..constants import OndertekeningSoorten, Statussen
from .factories import EnkelvoudigInformatieObjectFactory


@override_settings(ALLOWED_HOSTS=["testserver"])
class EnkelvoudigInformatieObjectTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def assertGegevensGroepRequired(
        self, url: str, field: str, base_body: dict, cases: tuple
    ):
        for key, code in cases:
            with self.subTest(key=key, expected_code=code):
                body = deepcopy(base_body)
                del body[key]
                response = self.client.post(url, {field: body})

                error = get_validation_errors(response, f"{field}.{key}")
                self.assertEqual(error["code"], code)

    def assertGegevensGroepValidation(
        self, url: str, field: str, base_body: dict, cases: tuple
    ):
        for key, code, blank_value in cases:
            with self.subTest(key=key, expected_code=code):
                body = deepcopy(base_body)
                body[key] = blank_value
                response = self.client.post(url, {field: body})

                error = get_validation_errors(response, f"{field}.{key}")
                self.assertEqual(error["code"], code)

    def test_validate_informatieobjecttype_invalid(self):
        ServiceFactory.create(api_root="https://example.com/", api_type=APITypes.ztc)
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.post(
            url,
            {"informatieobjecttype": "https://example.com/informatieobjecttype/foo"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "bad-url")

    @requests_mock.Mocker()
    def test_validate_informatieobjecttype_invalid_resource(self, m):
        ServiceFactory.create(api_root="https://example.com/", api_type=APITypes.ztc)
        m.get("https://example.com/", text="<html><head></head><body></body></html>")
        url = reverse("enkelvoudiginformatieobject-list")

        with requests_mock.Mocker() as m:
            m.get("https://example.com/", status_code=200, text="<html></html>")

            response = self.client.post(
                url, {"informatieobjecttype": "https://example.com/"}
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_validate_informatieobjecttype_unpublished(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.post(
            url,
            {"informatieobjecttype": f"http://testserver{informatieobjecttype_url}"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "not-published")

    def test_integriteit(self):
        url = reverse("enkelvoudiginformatieobject-list")

        base_body = {"algoritme": "MD5", "waarde": "foobarbaz", "datum": "2018-12-13"}

        cases = (
            ("algoritme", "required"),
            ("waarde", "required"),
            ("datum", "required"),
        )

        self.assertGegevensGroepRequired(url, "integriteit", base_body, cases)

    def test_integriteit_bad_values(self):
        url = reverse("enkelvoudiginformatieobject-list")

        base_body = {"algoritme": "MD5", "waarde": "foobarbaz", "datum": "2018-12-13"}

        cases = (
            ("algoritme", "invalid_choice", ""),
            ("waarde", "blank", ""),
            ("datum", "null", None),
        )

        self.assertGegevensGroepValidation(url, "integriteit", base_body, cases)

    def test_ondertekening(self):
        url = reverse("enkelvoudiginformatieobject-list")

        base_body = {"soort": OndertekeningSoorten.analoog, "datum": "2018-12-13"}

        cases = (("soort", "required"), ("datum", "required"))

        self.assertGegevensGroepRequired(url, "ondertekening", base_body, cases)

    def test_ondertekening_bad_values(self):
        url = reverse("enkelvoudiginformatieobject-list")

        base_body = {"soort": OndertekeningSoorten.digitaal, "datum": "2018-12-13"}
        cases = (("soort", "invalid_choice", ""), ("datum", "null", None))

        self.assertGegevensGroepValidation(url, "ondertekening", base_body, cases)

    def test_update_informatieobjecttype_success(self):
        """changed in Documenten 1.3 - eio.informatieobject is now mutable"""
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)

        iotype = InformatieObjectTypeFactory.create(concept=False)
        iotype_url = reverse(iotype)
        lock = self.client.post(f"{eio_url}/lock").data["lock"]

        response = self.client.patch(
            eio_url,
            {"informatieobjecttype": f"http://testserver{iotype_url}", "lock": lock},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(eio.canonical.latest_version.informatieobjecttype, iotype)

    @temp_private_root()
    def test_inhoud_incorrect_padding(self):
        iotype = InformatieObjectTypeFactory.create(concept=False)
        iotype_url = reverse(iotype)

        url = reverse("enkelvoudiginformatieobject-list")
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            # Remove padding from the base64 data
            "inhoud": b64encode(b"some file content").decode("utf-8")[:-1],
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{iotype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(url, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "inhoud")
        self.assertEqual(error["code"], "incorrect-base64-padding")

    @temp_private_root()
    def test_inhoud_correct_padding(self):
        iotype = InformatieObjectTypeFactory.create(concept=False)
        iotype_url = reverse(iotype)

        url = reverse("enkelvoudiginformatieobject-list")
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            # Remove padding from the base64 data
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{iotype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_rsin_identificatie(self):
        EnkelvoudigInformatieObjectFactory.create(
            identificatie="123456", bronorganisatie="159351741"
        )

        iotype = InformatieObjectTypeFactory.create(concept=False)
        iotype_url = reverse(iotype)

        url = reverse("enkelvoudiginformatieobject-list")
        content = {
            "identificatie": "123456",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            # Remove padding from the base64 data
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{iotype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(url, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "identificatie")
        self.assertEqual(error["code"], "identificatie-niet-uniek")
        self.assertEqual(
            error["reason"],
            _(
                "Deze identificatie ({identificatie}) bestaat al voor deze bronorganisatie"
            ).format(identificatie="123456"),
        )


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class InformatieObjectStatusTests(JWTAuthMixin, APITestCase):

    url = reverse_lazy("enkelvoudiginformatieobject-list")
    heeft_alle_autorisaties = True

    def test_ontvangen_informatieobjecten(self):
        """
        Assert certain statuses are not allowed for received documents.

        RGBZ 2.00.02 deel II Concept 20180613: De waarden ?in bewerking?
        en ?ter vaststelling? zijn niet van toepassing op ontvangen
        informatieobjecten.
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        invalid_statuses = (Statussen.in_bewerking, Statussen.ter_vaststelling)
        data = {
            "bronorganisatie": "319582462",
            "creatiedatum": "2018-12-24",
            "titel": "dummy",
            "auteur": "dummy",
            "taal": "nld",
            "inhoud": "aGVsbG8gd29ybGQ=",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "ontvangstdatum": "2018-12-24",
        }

        for invalid_status in invalid_statuses:
            with self.subTest(status=invalid_status):
                _data = data.copy()
                _data["status"] = invalid_status

                response = self.client.post(self.url, _data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            error = get_validation_errors(response, "status")
            self.assertEqual(error["code"], "invalid_for_received")

    def test_informatieobjecten_niet_ontvangen(self):
        """
        All statusses should be allowed when the informatieobject doesn't have
        a receive date.
        """
        for valid_status, message in Statussen.choices:
            with self.subTest(status=status):
                data = {"ontvangstdatum": None, "status": valid_status}

                response = self.client.post(self.url, data)

            error = get_validation_errors(response, "status")
            self.assertIsNone(error)

    def test_status_set_ontvangstdatum_is_set_later(self):
        """
        Assert that setting the ontvangstdatum later, after an 'invalid' status
        has been set, is not possible.
        """
        eio = EnkelvoudigInformatieObjectFactory.create(ontvangstdatum=None)
        url = reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid})

        for invalid_status in (Statussen.in_bewerking, Statussen.ter_vaststelling):
            with self.subTest(status=invalid_status):
                eio.status = invalid_status
                eio.save()
                data = {"ontvangstdatum": "2018-12-24"}

                response = self.client.patch(url, data)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                error = get_validation_errors(response, "status")
                self.assertEqual(error["code"], "invalid_for_received")


class UpdateStatusDefinitiefTests(JWTAuthMixin, APITestCase):
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        super().setUpTestData()

    def test_update_definitief_status_success(self):
        self.autorisatie.scopes = [
            SCOPE_DOCUMENTEN_ALLES_LEZEN,
            SCOPE_DOCUMENTEN_BIJWERKEN,
            SCOPE_DOCUMENTEN_LOCK,
        ]
        self.autorisatie.save()
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype, status=Statussen.definitief
        )
        eio_url = reverse(eio)

        eio_response = self.client.get(eio_url)
        eio_data = eio_response.data

        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        eio_data.update(
            {
                "inhoud": b64encode(b"aaaaa"),
                "bestandsomvang": 5,
                "lock": lock,
            }
        )
        for i in ["integriteit", "ondertekening"]:
            eio_data.pop(i)

        response = self.client.put(eio_url, eio_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_definitief_status_success(self):
        self.autorisatie.scopes = [
            SCOPE_DOCUMENTEN_ALLES_LEZEN,
            SCOPE_DOCUMENTEN_BIJWERKEN,
            SCOPE_DOCUMENTEN_LOCK,
        ]
        self.autorisatie.save()
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype, status=Statussen.definitief
        )
        eio_url = reverse(eio)
        lock = self.client.post(f"{eio_url}/lock").data["lock"]

        response = self.client.patch(
            eio_url,
            {
                "lock": lock,
                "beschrijving": "updated",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@tag("oio")
class FilterValidationTests(JWTAuthMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_oio_invalid_filters(self):
        url = reverse("objectinformatieobject-list")

        invalid_filters = {
            "object": "123",  # must be url
            "informatieobject": "123",  # must be url
            "foo": "bar",  # unknown
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(
                    url, {key: value}, headers={"accept-crs": "EPSG:4326"}
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
