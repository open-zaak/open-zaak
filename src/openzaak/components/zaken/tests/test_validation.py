# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import datetime

from django.test import override_settings
from django.utils.timezone import make_aware

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    Archiefstatus,
    BrondatumArchiefprocedureAfleidingswijze,
    RolTypes,
)
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin, patch_resource_validator

from ..models import ZaakInformatieObject
from .factories import (
    ResultaatFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import isodatetime


class ZaakInformatieObjectValidationTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_informatieobject_invalid(self):
        ServiceFactory.create(api_root="https://drc.nl/", api_type=APITypes.drc)
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

    def test_zaak_is_archived(self):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        io = EnkelvoudigInformatieObjectFactory.create()
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "informatieobject": f"http://testserver{reverse(io)}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


class StatusValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_root="https://external.nl/", api_type=APITypes.ztc)
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
        ServiceFactory.create(
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
        ServiceFactory.create(api_root="https://example.com/", api_type=APITypes.ztc)
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

    def test_zaak_is_archived(self):
        zaak = ZaakFactory.create(
            archiefstatus=Archiefstatus.gearchiveerd, zaaktype=self.zaaktype
        )
        url = reverse("status-list")

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


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
        ServiceFactory.create(
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
        ServiceFactory.create(api_root="https://example.com/", api_type=APITypes.ztc)
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

    def test_zaak_is_archived(self):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)

        url = reverse("resultaat-list")

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "resultaattype": f"http://testserver{reverse(resultaattype)}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


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
        ServiceFactory.create(api_root="http://example.com/", api_type=APITypes.ztc)
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

    def test_zaak_is_archived(self):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        eigenschap = EigenschapFactory.create(zaaktype=zaak.zaaktype)

        url = reverse("zaakeigenschap-list", kwargs={"zaak_uuid": zaak.uuid})

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "eigenschap": f"http://testserver{reverse(eigenschap)}",
                "waarde": "test",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


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

    @requests_mock.Mocker()
    def test_zaak_is_archived(self, m):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        m.get(
            "http://some-api.com/objecten/1234",
            json={"url": "http://some-api.com/objecten/1234"},
        )
        url = reverse("zaakobject-list")

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "object": "http://some-api.com/objecten/1234",
                "objectType": "adres",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


class RolValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaak_is_archived(self):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)

        url = reverse("rol-list")

        response = self.client.post(
            url,
            {
                "zaak": f"http://testserver{reverse(zaak)}",
                "roltype": f"http://testserver{reverse(roltype)}",
                "betrokkene": "http://www.example.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                "betrokkene_type": RolTypes.natuurlijk_persoon,
                "roltoelichting": "test",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


class ZaakContactMomentValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch_resource_validator
    @requests_mock.Mocker()
    def test_zaak_is_archived(self, *mocks):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        contactmoment = "https://contactmomenten.nl/api/v1/contactmomenten/1234"
        url = reverse("zaakcontactmoment-list")

        with requests_mock.Mocker() as m:
            m.get(contactmoment, json={"url": contactmoment})

            response = self.client.post(
                url,
                {
                    "zaak": f"http://testserver{reverse(zaak)}",
                    "contactmoment": contactmoment,
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")


class ZaakVerzoekValidationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch_resource_validator
    @requests_mock.Mocker()
    def test_zaak_is_archived(self, *mocks):
        zaak = ZaakFactory.create(archiefstatus=Archiefstatus.gearchiveerd)
        verzoek = "https://verzoeken.nl/api/v1/verzoeken/1234"
        url = reverse("zaakverzoek-list")

        with requests_mock.Mocker() as m:
            m.get(verzoek, json={"url": verzoek})

            response = self.client.post(
                url,
                {
                    "zaak": f"http://testserver{reverse(zaak)}",
                    "verzoek": verzoek,
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaak-archiefstatus-invalid")
