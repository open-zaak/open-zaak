import uuid
from datetime import datetime

from django.test import tag
from django.utils import timezone

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RelatieAarden
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.catalogi.tests.factories import ZaakInformatieobjectTypeFactory
from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import (
    get_eio_response,
    get_oio_response,
)
from openzaak.utils.tests import JWTAuthMixin

from ..models import Zaak, ZaakInformatieObject
from .factories import ZaakFactory, ZaakInformatieObjectFactory


class ZaakInformatieObjectAPITests(JWTAuthMixin, APITestCase):

    list_url = reverse(ZaakInformatieObject)
    heeft_alle_autorisaties = True

    @freeze_time("2018-09-19T12:25:19+0200")
    def test_create(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakInformatieobjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        titel = "some titel"
        beschrijving = "some beschrijving"
        content = {
            "informatieobject": f"http://testserver{io_url}",
            "zaak": f"http://testserver{zaak_url}",
            "titel": titel,
            "beschrijving": beschrijving,
            "aardRelatieWeergave": "bla",  # Should be ignored by the API
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

        expected_url = reverse(stored_object)

        expected_response = content.copy()
        expected_response.update(
            {
                "url": f"http://testserver{expected_url}",
                "uuid": str(stored_object.uuid),
                "titel": titel,
                "beschrijving": beschrijving,
                "registratiedatum": "2018-09-19T10:25:19Z",
                "aardRelatieWeergave": RelatieAarden.labels[RelatieAarden.hoort_bij],
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, "informatieobject", index=1)
        self.assertEqual(error["code"], "bad-url")

    @freeze_time("2018-09-20 12:00:00")
    def test_registratiedatum_ignored(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakInformatieobjectTypeFactory.create(
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
        zio_type = ZaakInformatieobjectTypeFactory.create(
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
            "aardRelatieWeergave": RelatieAarden.labels[RelatieAarden.hoort_bij],
            "titel": "",
            "beschrijving": "",
            "registratiedatum": "2018-09-20T12:00:00Z",
        }

        self.assertEqual(response.json(), expected)

    def test_filter_by_zaak(self):
        zio = ZaakInformatieObjectFactory.create()
        zaak_url = reverse(zio.zaak)
        zio_list_url = reverse("zaakinformatieobject-list")

        response = self.client.get(
            zio_list_url,
            {"zaak": f"http://openzaak.nl{zaak_url}"},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], f"http://openzaak.nl{zaak_url}")

    def test_filter_by_local_informatieobject(self):
        zio = ZaakInformatieObjectFactory.create()
        io_url = reverse(zio.informatieobject.latest_version)
        zio_list_url = reverse("zaakinformatieobject-list")

        response = self.client.get(
            zio_list_url,
            {"informatieobject": f"http://openzaak.nl{io_url}"},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["informatieobject"], f"http://openzaak.nl{io_url}"
        )

    def test_filter_by_external_informatieobject(self):
        base = "https://external.documenten.nl/api/v1/"
        document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakInformatieobjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://testserver{reverse(zio_type.informatieobjecttype)}",
        )

        with requests_mock.Mocker() as m:
            m.get(document, json=eio_response)
            m.post(
                "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                json=get_oio_response(document, zaak_url),
                status_code=201,
            )

            response = self.client.post(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url, "informatieobject": document},
            )

        io_url = response.data["informatieobject"]
        zio_list_url = reverse("zaakinformatieobject-list")

        response = self.client.get(
            zio_list_url, {"informatieobject": io_url}, HTTP_HOST="openzaak.nl"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], io_url)

    def test_update_zaak(self):
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


@tag("external-urls")
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    # TODO: validation tests with bad inputs

    def test_relate_external_document(self):
        base = "https://external.documenten.nl/api/v1/"
        document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        zio_type = ZaakInformatieobjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zaak = ZaakFactory.create(zaaktype=zio_type.zaaktype)
        zaak_url = f"http://openzaak.nl{reverse(zaak)}"
        eio_response = get_eio_response(
            document,
            informatieobjecttype=f"http://testserver{reverse(zio_type.informatieobjecttype)}",
        )

        with self.subTest(section="zio-create"):
            with requests_mock.Mocker() as m:
                m.get(document, json=eio_response)
                m.post(
                    "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                    json=get_oio_response(document, zaak_url),
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

        with self.subTest(section="zio-list"):
            list_response = self.client.get(
                reverse(ZaakInformatieObject),
                {"zaak": zaak_url},
                HTTP_HOST="openzaak.nl",
            )

            self.assertEqual(list_response.status_code, status.HTTP_200_OK)
            data = list_response.json()

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["informatieobject"], document)
