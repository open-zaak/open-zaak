# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import concurrent.futures
import uuid
from datetime import datetime
from unittest.mock import patch

from django.db import close_old_connections
from django.test import override_settings, tag
from django.test.utils import override_script_prefix
from django.utils import timezone

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.constants import RelatieAarden
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from vng_api_common.validators import IsImmutableValidator
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import (
    get_catalogus_response,
    get_informatieobjecttype_response,
    get_oio_response,
)
from openzaak.tests.utils import JWTAuthMixin, get_eio_response, mock_drc_oas_get

from ..models import Zaak, ZaakInformatieObject
from .factories import StatusFactory, ZaakFactory, ZaakInformatieObjectFactory
from .utils import get_zaaktype_response


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ZaakInformatieObjectAPITests(JWTAuthMixin, APITestCase):

    list_url = reverse_lazy(ZaakInformatieObject)
    heeft_alle_autorisaties = True

    @freeze_time("2018-09-19T12:25:19+0200")
    def test_create(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        status_ = StatusFactory.create(zaak=zaak)
        status_url = reverse(status_)

        titel = "some titel"
        beschrijving = "some beschrijving"
        content = {
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
            "titel": titel,
            "beschrijving": beschrijving,
            "aardRelatieWeergave": "bla",  # Should be ignored by the API
            "status": f"http://testserver{status_url}",
            "vernietigingsdatum": "2023-01-02T00:00",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        self.assertEqual(ZaakInformatieObject.objects.count(), 1)
        stored_object = ZaakInformatieObject.objects.get()
        self.assertEqual(stored_object.zaak, zaak)
        self.assertEqual(stored_object.aard_relatie, RelatieAarden.hoort_bij)
        self.assertEqual(stored_object.status, status_)
        self.assertEqual(
            stored_object.vernietigingsdatum.isoformat(), "2023-01-02T00:00:00+00:00"
        )

        expected_url = reverse(stored_object)

        expected_response = content.copy()
        expected_response.update(
            {
                "url": f"http://testserver{expected_url}",
                "uuid": str(stored_object.uuid),
                "titel": titel,
                "beschrijving": beschrijving,
                "registratiedatum": "2018-09-19T10:25:19Z",
                "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
                "vernietigingsdatum": "2023-01-02T00:00:00Z",
            }
        )

        self.assertEqual(response.json(), expected_response)

    def test_create_invalid_informatieobject(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)

        content = {
            "zaak": f"http://testserver{zaak_url}",
            "informatieobject": "invalidurl",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "bad-url")

    @freeze_time("2018-09-20 12:00:00")
    def test_registratiedatum_ignored(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        content = {
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
            "registratiedatum": "2018-09-19T12:25:20+0200",
        }

        # Send to the API
        self.client.post(self.list_url, content)

        oio = ZaakInformatieObject.objects.get()

        self.assertEqual(
            oio.registratiedatum,
            datetime(2018, 9, 20, 12, 0, 0).replace(tzinfo=timezone.utc),
        )

    def test_duplicate_object(self):
        """
        Test the (informatieobject, object) unique together validation.
        """
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zio = ZaakInformatieObjectFactory.create(
            zaak__zaaktype=zio_type.zaaktype,
            informatieobject__latest_version__informatieobjecttype=zio_type.informatieobjecttype,
        )
        zaak_url = reverse(zio.zaak)
        io_url = reverse(zio.informatieobject.latest_version)

        content = {
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    @freeze_time("2018-09-20 12:00:00")
    def test_read_zaak(self):
        zio = ZaakInformatieObjectFactory.create()
        zio_detail_url = reverse(zio)

        response = self.client.get(zio_detail_url)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaak_url = reverse(zio.zaak)
        io_url = reverse(zio.informatieobject.latest_version)
        expected = {
            "url": f"http://testserver{zio_detail_url}",
            "uuid": str(zio.uuid),
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
            "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
            "titel": "",
            "beschrijving": "",
            "registratiedatum": "2018-09-20T12:00:00Z",
            "status": None,
            "vernietigingsdatum": None,
        }

        self.assertEqual(response.json(), expected)

    def test_filter_by_zaak(self):
        zio = ZaakInformatieObjectFactory.create()
        zaak_url = reverse(zio.zaak)
        zio_list_url = reverse("zaakinformatieobject-list")

        response = self.client.get(
            zio_list_url,
            {"zaak": f"http://openzaak.nl{zaak_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], f"http://openzaak.nl{zaak_url}")

    def test_filter_by_local_informatieobject(self):
        zio_list_url = reverse("zaakinformatieobject-list")

        zio1 = ZaakInformatieObjectFactory.create()
        io1_url = reverse(zio1.informatieobject.latest_version)

        ZaakInformatieObjectFactory.create()

        response = self.client.get(
            zio_list_url,
            {"informatieobject": f"http://openzaak.nl{io1_url}"},
            headers={"host": "openzaak.nl"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["informatieobject"], f"http://openzaak.nl{io1_url}"
        )

    def test_filter_by_external_informatieobject(self):
        base = "https://external.documenten.nl/api/v1/"
        document1 = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        document2 = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=base,
            label="external documents",
            auth_type=AuthTypes.no_auth,
        )

        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"

        eio1_response = get_eio_response(
            document1,
            informatieobjecttype=f"http://openzaak.nl{reverse(zio_type.informatieobjecttype)}",
        )
        eio2_response = get_eio_response(
            document2,
            informatieobjecttype=f"http://openzaak.nl{reverse(zio_type.informatieobjecttype)}",
        )

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            mock_service_oas_get(m, base, "drc")
            m.get(document1, json=eio1_response)
            m.post(
                "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                json=get_oio_response(document1, zaak_url),
                status_code=201,
            )

            m.get(document2, json=eio2_response)
            m.post(
                "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                json=get_oio_response(document2, zaak_url),
                status_code=201,
            )

            response1 = self.client.post(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url, "informatieobject": document1},
                headers={"host": "openzaak.nl"},
            )
            self.client.post(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url, "informatieobject": document2},
                headers={"host": "openzaak.nl"},
            )

        io1_url = response1.data["informatieobject"]
        zio_list_url = reverse("zaakinformatieobject-list")

        # Test that only 1 of the 2 ZIOs in the database is returned.
        response = self.client.get(
            zio_list_url, {"informatieobject": io1_url}, headers={"host": "openzaak.nl"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], io1_url)

    def test_update_zaak_and_informatieobject_fails(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        zio = ZaakInformatieObjectFactory.create()
        zio_detail_url = reverse(zio)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        response = self.client.put(
            zio_detail_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        for field in ["zaak", "informatieobject"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], IsImmutableValidator.code)

    def test_partial_update_zaak_and_informatieobject_fails(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        zio = ZaakInformatieObjectFactory.create()
        zio_detail_url = reverse(zio)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        response = self.client.patch(
            zio_detail_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        for field in ["zaak", "informatieobject"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], IsImmutableValidator.code)

    def test_update_zio_metadata(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )

        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak, informatieobject=io.canonical
        )
        zio_detail_url = reverse(zio)

        response = self.client.put(
            zio_detail_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": f"http://testserver{io_url}",
                "titel": "updated title",
                "beschrijving": "same",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["titel"], "updated title")
        self.assertEqual(response.data["beschrijving"], "same")

        zio.refresh_from_db()
        self.assertEqual(zio.titel, "updated title")
        self.assertEqual(zio.beschrijving, "same")

    def test_partial_update_zio_metadata(self):
        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create()

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )

        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak, informatieobject=io.canonical
        )
        zio_detail_url = reverse(zio)

        response = self.client.patch(
            zio_detail_url, {"titel": "updated title", "beschrijving": "same"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["titel"], "updated title")
        self.assertEqual(response.data["beschrijving"], "same")

        zio.refresh_from_db()
        self.assertEqual(zio.titel, "updated title")
        self.assertEqual(zio.beschrijving, "same")

    @freeze_time("2018-09-19T12:25:19+0200")
    def test_delete(self):
        zio = ZaakInformatieObjectFactory.create()
        zio_url = reverse(zio)

        response = self.client.delete(zio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        # Relation is gone, zaak still exists.
        self.assertFalse(ZaakInformatieObject.objects.exists())
        self.assertTrue(Zaak.objects.exists())


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
@tag("external-urls")
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    base = "https://external.documenten.nl/api/v1/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=cls.base,
            label="external documents",
            auth_type=AuthTypes.no_auth,
        )

    def test_relate_external_document(self):
        document = f"{self.base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://testserver{reverse(zio_type.informatieobjecttype)}",
        )
        oio_response = get_oio_response(document, zaak_url)

        with self.subTest(section="zio-create"):
            with requests_mock.Mocker() as m:
                mock_service_oas_get(m, self.base, "drc")
                m.get(document, json=eio_response)
                m.post(
                    "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                    json=oio_response,
                    status_code=201,
                )

                response = self.client.post(
                    reverse(ZaakInformatieObject),
                    {"zaak": zaak_url, "informatieobject": document},
                )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

            posts = [req for req in m.request_history if req.method == "POST"]
            self.assertEqual(len(posts), 1)
            request = posts[0]
            self.assertEqual(
                request.url,
                "https://external.documenten.nl/api/v1/objectinformatieobjecten",
            )
            self.assertEqual(
                request.json(),
                {
                    "informatieobject": document,
                    "object": zaak_url,
                    "objectType": "zaak",
                },
            )

            self.assertFalse(ObjectInformatieObject.objects.exists())

            zio = ZaakInformatieObject.objects.get()
            self.assertEqual(zio._objectinformatieobject_url, oio_response["url"])

        with self.subTest(section="zio-list"):
            list_response = self.client.get(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url},
                headers={"host": "openzaak.nl"},
            )

            self.assertEqual(list_response.status_code, status.HTTP_200_OK)
            data = list_response.json()

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["informatieobject"], document)

    def test_create_zio_fail_bad_url(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        list_url = reverse(ZaakInformatieObject)
        data = {"zaak": zaak_url, "informatieobject": "abcd"}

        response = self.client.post(list_url, data, headers={"host": "openzaak.nl"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "bad-url")

    @override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
    def test_create_zio_fail_not_json(self):
        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root="http://example.com/",
            auth_type=AuthTypes.no_auth,
        )
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        list_url = reverse(ZaakInformatieObject)
        data = {"zaak": zaak_url, "informatieobject": "http://example.com/"}

        with requests_mock.Mocker() as m:
            m.get("http://example.com/", text="<html></html>")
            response = self.client.post(list_url, data, headers={"host": "openzaak.nl"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_zio_fail_invalid_schema(self):
        base = "https://external.documenten.nl/api/v1/"
        document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(
                document,
                json={
                    "url": document,
                    "beschrijving": "",
                    "ontvangstdatum": None,
                    "informatieobjecttype": f"http://testserver{reverse(zio_type.informatieobjecttype)}",
                    "locked": False,
                },
            )

            response = self.client.post(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url, "informatieobject": document},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid-resource")

    @requests_mock.Mocker()
    def test_update_zio_metadata(self, m):
        mock_drc_oas_get(m)
        document = f"{self.base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://testserver{reverse(zio_type.informatieobjecttype)}",
        )
        m.get(document, json=eio_response)
        zio = ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=document)
        zio_detail_url = reverse(zio)

        response = self.client.put(
            zio_detail_url,
            {
                "zaak": zaak_url,
                "informatieobject": document,
                "titel": "updated title",
                "beschrijving": "same",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["titel"], "updated title")
        self.assertEqual(response.data["beschrijving"], "same")

        zio.refresh_from_db()
        self.assertEqual(zio.titel, "updated title")
        self.assertEqual(zio.beschrijving, "same")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalDocumentsAPITransactionTests(JWTAuthMixin, APITransactionTestCase):
    heeft_alle_autorisaties = True
    base = "https://external.documenten.nl/api/v1/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Service.objects.update_or_create(
            api_root=cls.base,
            defaults=dict(
                api_type=APITypes.drc,
                slug=cls.base,
                label="external documents",
                auth_type=AuthTypes.no_auth,
            ),
        )

        cls.setUpTestData()

    @tag("gh-819")
    def test_zio_visibility_outside_transaction(self):
        """
        Test that the ZIO being created is visible to an external DRC.

        This is a regression test for #819 - because of the DB transaction wrapping,
        API calls requesting ZIO don't actually see the object yet, leading to
        validation errors. We simulate this by using threading to get a different
        DB connection, outside of the possible current transaction.
        """
        document = f"{self.base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://testserver{reverse(zio_type.informatieobjecttype)}",
        )

        def worker(zaak_id: int):
            """
            Worker to run in a thread.

            When this worker runs, there should be one ZIO visible in the database - it
            must have been committed so that the remote DRC can view this record too.
            """
            zios = ZaakInformatieObject.objects.filter(zaak__id=zaak_id)
            self.assertEqual(zios.count(), 1)
            close_old_connections()

        def mock_create_remote_oio(*args, **kwargs):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(worker, zaak.id)
                future.result()  # raises any exceptions, such as assertionerrors
            return {"url": f"{self.base}objectinformatieobjecten/{uuid.uuid4()}"}

        with patch(
            "openzaak.components.zaken.api.serializers.zaken.create_remote_oio",
            side_effect=mock_create_remote_oio,
        ):
            with requests_mock.Mocker() as m:
                mock_drc_oas_get(m)
                m.get(document, json=eio_response)

                response = self.client.post(
                    reverse(ZaakInformatieObject),
                    {"zaak": zaak_url, "informatieobject": document},
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ExternalInformatieObjectAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    list_url = reverse_lazy(ZaakInformatieObject)
    base = "https://external.documenten.nl/api/v1/"
    document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=cls.base,
            label="external documents",
            auth_type=AuthTypes.no_auth,
        )
        ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root="http://openzaak.nl/catalogi/api/v1/",
        )

    def test_zaaktype_internal_iotype_internal_fail(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        informatieobjecttype = InformatieObjectTypeFactory.create()
        eio_response = get_eio_response(
            self.document,
            informatieobjecttype=f"http://openzaak.nl{reverse(informatieobjecttype)}",
        )

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(self.document, json=eio_response)
            response = self.client.post(
                self.list_url,
                {"zaak": zaak_url, "informatieobject": self.document},
                headers={"host": "openzaak.nl"},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_zaaktype_external_iotype_external_success(self):
        catalogus = f"{self.base}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = f"{self.base}zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        informatieobjecttype = f"{self.base}informatieobjecttypen/{uuid.uuid4()}"
        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)
        zaaktype_data["informatieobjecttypen"] = [informatieobjecttype]

        with requests_mock.Mocker() as m:
            mock_service_oas_get(m, self.base, "drc")
            m.get(zaaktype, json=zaaktype_data)
            m.get(
                informatieobjecttype,
                json=get_informatieobjecttype_response(catalogus, informatieobjecttype),
            )
            m.get(
                self.document,
                json=get_eio_response(
                    self.document, informatieobjecttype=informatieobjecttype
                ),
            )
            m.post(
                f"{self.base}objectinformatieobjecten",
                json=get_oio_response(self.document, zaak_url),
                status_code=201,
            )

            response = self.client.post(
                self.list_url,
                {"zaak": zaak_url, "informatieobject": self.document},
                headers={"host": "openzaak.nl"},
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_zaaktype_external_iotype_external_fail(self):
        catalogus = f"{self.base}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = f"{self.base}zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        informatieobjecttype = f"{self.base}informatieobjecttypen/{uuid.uuid4()}"

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(
                informatieobjecttype,
                json=get_informatieobjecttype_response(catalogus, informatieobjecttype),
            )
            m.get(
                self.document,
                json=get_eio_response(
                    self.document, informatieobjecttype=informatieobjecttype
                ),
            )

            response = self.client.post(
                self.list_url,
                {"zaak": zaak_url, "informatieobject": self.document},
                headers={"host": "openzaak.nl"},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_zaaktype_internal_iotype_external(self):
        zaak = ZaakFactory.create()
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        informatieobjecttype = f"{self.base}informatieobjecttypen/{uuid.uuid4()}"
        catalogus = f"{self.base}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(
                informatieobjecttype,
                json=get_informatieobjecttype_response(catalogus, informatieobjecttype),
            )
            m.get(
                catalogus, json=get_catalogus_response(catalogus, informatieobjecttype)
            )
            m.get(
                self.document,
                json=get_eio_response(
                    self.document, informatieobjecttype=informatieobjecttype
                ),
            )

            response = self.client.post(
                self.list_url,
                {"zaak": zaak_url, "informatieobject": self.document},
                headers={"host": "openzaak.nl"},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_zaaktype_external_iotype_internal(self):
        catalogus = f"{self.base}catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = f"{self.base}zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        informatieobjecttype = InformatieObjectTypeFactory.create()
        eio_response = get_eio_response(
            self.document,
            informatieobjecttype=f"http://openzaak.nl{reverse(informatieobjecttype)}",
        )

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(self.document, json=eio_response)

            response = self.client.post(
                self.list_url,
                {"zaak": zaak_url, "informatieobject": self.document},
                headers={"host": "openzaak.nl"},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ExternalDocumentDestroyTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    list_url = reverse_lazy(ZaakInformatieObject)
    base = "https://external.documenten.nl/api/v1/"
    document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=cls.base,
            label="external documents",
            auth_type=AuthTypes.no_auth,
        )
        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root="http://openzaak.nl/catalogi/api/v1/",
        )

    def test_destroy_with_external_informatieobject(self):
        oio = f"{self.base}objectinformatieobjecten/{uuid.uuid4()}"
        informatieobjecttype = InformatieObjectTypeFactory.create()

        with requests_mock.Mocker() as m:
            mock_service_oas_get(m, self.base, "drc")
            m.get(
                self.document,
                json=get_eio_response(
                    self.document,
                    informatieobjecttype=f"http://openzaak.nl{reverse(informatieobjecttype)}",
                ),
            )
            m.delete(oio, status_code=204)

            zio = ZaakInformatieObjectFactory.create(
                informatieobject=self.document, _objectinformatieobject_url=oio
            )
            zio_url = reverse(zio)

            response = self.client.delete(zio_url, headers={"host": "openzaak.nl"})

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertEqual(ZaakInformatieObject.objects.count(), 0)

        history_delete = [
            req
            for req in m.request_history
            if req.method == "DELETE" and req.url == oio
        ]
        self.assertEqual(len(history_delete), 1)

    def test_destroy_with_external_informatieobject_fail_send(self):
        oio = f"{self.base}objectinformatieobjecten/{uuid.uuid4()}"
        informatieobjecttype = InformatieObjectTypeFactory.create()

        with requests_mock.Mocker() as m:
            mock_service_oas_get(m, self.base, "drc")
            m.get(
                self.document,
                json=get_eio_response(
                    self.document,
                    informatieobjecttype=f"http://openzaak.nl{reverse(informatieobjecttype)}",
                ),
            )
            m.delete(oio, status_code=404, text="Not found")

            zio = ZaakInformatieObjectFactory.create(
                informatieobject=self.document, _objectinformatieobject_url=oio
            )
            zio_url = reverse(zio)

            response = self.client.delete(zio_url, headers={"host": "openzaak.nl"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "pending-relations")

    def test_representation(self):
        zio = ZaakInformatieObjectFactory.create()
        zio_representation = str(zio)
        expected_representation = f"{zio.zaak.identificatie} - {zio.informatieobject.latest_version.identificatie}"
        self.assertEqual(expected_representation, zio_representation)


@tag("external-urls")
class ExternalInformatieObjectSameDomainTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @override_settings(
        ALLOWED_HOSTS=["api.example.nl"],
        LOOSE_FK_LOCAL_BASE_URLS=[
            "http://api.example.nl/ozgv-t/zaken/",
            "http://api.example.nl/ozgv-t/catalogi/",
        ],
        FORCE_SCRIPT_NAME="/ozgv-t",
    )
    def test_zaaktype_internal_iotype_external_same_domain(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1592
        """

        document_api_root = "http://api.example.nl/ozgv-t/documenten/service/drc/v1/"
        document = f"{document_api_root}enkelvoudiginformatieobjecten/be0a31c7-6c9c-4d75-aefd-db950be62267"

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=document_api_root,
            label="external documents",
            auth_type=AuthTypes.zgw,
            client_id="a-client-id",
            secret="secret",
        )
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://api.example.nl/ozgv-t{reverse(zaak)}"
        # for mocks
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://api.example.nl/ozgv-t{reverse(zio_type.informatieobjecttype)}",
        )
        oio_response = get_oio_response(document, zaak_url)

        data = {"zaak": zaak_url, "informatieobject": document}
        ziot_list_url = reverse(ZaakInformatieObject)

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(document, json=eio_response)
            m.post(
                f"{document_api_root}objectinformatieobjecten",
                json=oio_response,
                status_code=201,
            )

            with override_script_prefix(prefix="/ozgv-t"):
                response = self.client.post(
                    ziot_list_url, data, headers={"host": "api.example.nl"}
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zio = ZaakInformatieObject.objects.get()
        self.assertEqual(zio.zaak, zaak)
        self.assertEqual(zio._informatieobject_url, document)

    @override_settings(
        ALLOWED_HOSTS=["api.example.nl"],
        LOOSE_FK_LOCAL_BASE_URLS=[
            "http://api.example.nl/ozgv-t/zaken/",
            "http://api.example.nl/ozgv-t/catalogi/",
        ],
        FORCE_SCRIPT_NAME="/ozgv-t",
    )
    def test_filter_by_external_informatieobject(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1830
        """

        document_api_root = "http://api.example.nl/ozgv-t/documenten/service/drc/v1/"
        document = f"{document_api_root}enkelvoudiginformatieobjecten/be0a31c7-6c9c-4d75-aefd-db950be62267"

        ServiceFactory.create(
            api_type=APITypes.drc,
            api_root=document_api_root,
            label="external documents",
            auth_type=AuthTypes.zgw,
            client_id="a-client-id",
            secret="secret",
        )
        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://api.example.nl/ozgv-t{reverse(zaak)}"
        # for mocks
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://api.example.nl/ozgv-t{reverse(zio_type.informatieobjecttype)}",
        )

        ziot_list_url = reverse(ZaakInformatieObject)

        with requests_mock.Mocker() as m:
            mock_drc_oas_get(m)
            m.get(document, json=eio_response)
            ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=document)

            with override_script_prefix(prefix="/ozgv-t"):
                response = self.client.get(
                    ziot_list_url,
                    {"informatieobject": document},
                    headers={"host": "api.example.nl"},
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], zaak_url)
        self.assertEqual(response.data[0]["informatieobject"], document)
