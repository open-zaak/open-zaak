from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import serialise_eio
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ..models import KlantContact, Resultaat, ZaakInformatieObject, ZaakObject
from .factories import (
    KlantContactFactory,
    ResultaatFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, isodatetime


@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectValidationCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_informatieobject_invalid(self):
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
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.register_uri("GET", io_url, json=serialise_eio(io, io_url))
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url, {"zaak": f"http://testserver{zaak_url}", "informatieobject": io_url,},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_informatieobject_fails(self):
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.register_uri("GET", io_url, json=serialise_eio(io, io_url))

        zio = ZaakInformatieObjectFactory.create(
            informatieobject=io_url,
            informatieobject__informatieobjecttype=io.informatieobjecttype,
        )
        zio_url = reverse(zio)

        response = self.client.patch(zio_url, {"informatieobject": io_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "informatieobject")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)


@override_settings(CMIS_ENABLED=True)
class FilterValidationCMISTests(JWTAuthMixin, APICMISTestCase):
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
        for counter in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()
            self.adapter.register_uri("GET", eio_url, json=serialise_eio(eio, eio_url))
            ZaakInformatieObjectFactory.create(informatieobject=eio_url)

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


@override_settings(CMIS_ENABLED=True)
class StatusValidationCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": "https://example.com",
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
        io = EnkelvoudigInformatieObjectFactory.create()
        io.canonical.lock_document(io.uuid)
        io_url = io.get_url()
        self.adapter.register_uri("GET", io_url, json=serialise_eio(io, io_url))
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
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
        io_url = io.get_url()
        self.adapter.register_uri("GET", io_url, json=serialise_eio(io, io_url))
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
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
