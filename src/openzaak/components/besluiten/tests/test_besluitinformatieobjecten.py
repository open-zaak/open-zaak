from django.test import tag, override_settings
import uuid
import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import JWTAuthMixin
from openzaak.components.documenten.tests.utils import get_eio_response, get_oio_response
from openzaak.components.documenten.models import ObjectInformatieObject

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory


class BesluitInformatieObjectAPITests(JWTAuthMixin, APITestCase):

    list_url = reverse_lazy("besluitinformatieobject-list", kwargs={"version": "1"})

    heeft_alle_autorisaties = True

    def test_create(self):
        besluit = BesluitFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = reverse(besluit)
        io_url = reverse(io)
        content = {
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        self.assertEqual(BesluitInformatieObject.objects.count(), 1)
        stored_object = BesluitInformatieObject.objects.get()
        self.assertEqual(stored_object.besluit, besluit)

        expected_url = reverse(stored_object)

        expected_response = content.copy()
        expected_response.update({"url": f"http://testserver{expected_url}"})
        self.assertEqual(response.json(), expected_response)

    def test_duplicate_object(self):
        """
        Test the (informatieobject, object) unique together validation.
        """
        bio = BesluitInformatieObjectFactory.create()
        besluit_url = reverse(bio.besluit)
        io_url = reverse(bio.informatieobject.latest_version)

        content = {
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_read_besluit(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_detail_url = reverse(bio)

        response = self.client.get(bio_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        besluit_url = reverse(bio.besluit)
        io_url = reverse(bio.informatieobject.latest_version)
        expected = {
            "url": f"http://testserver{bio_detail_url}",
            "informatieobject": f"http://testserver{io_url}",
            "besluit": f"http://testserver{besluit_url}",
        }

        self.assertEqual(response.json(), expected)

    def test_filter_by_besluit(self):
        bio = BesluitInformatieObjectFactory.create()
        besluit_url = reverse(bio.besluit)
        bio_list_url = reverse("besluitinformatieobject-list")

        response = self.client.get(
            bio_list_url,
            {"besluit": f"http://openzaak.nl{besluit_url}"},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["besluit"], f"http://openzaak.nl{besluit_url}"
        )

    def test_filter_by_informatieobject(self):
        bio = BesluitInformatieObjectFactory.create()
        io_url = reverse(bio.informatieobject.latest_version)
        bio_list_url = reverse("besluitinformatieobject-list")

        response = self.client.get(
            bio_list_url,
            {"informatieobject": f"http://openzaak.nl{io_url}"},
            HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["informatieobject"], f"http://openzaak.nl{io_url}"
        )

    def test_put_besluit_not_allowed(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_detail_url = reverse(bio)
        besluit = BesluitFactory.create()
        besluit_url = reverse(besluit)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        response = self.client.put(
            bio_detail_url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data
        )

    def test_patch_besluit_not_allowed(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_detail_url = reverse(bio)
        besluit = BesluitFactory.create()
        besluit_url = reverse(besluit)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)

        response = self.client.patch(
            bio_detail_url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data
        )

    def test_delete(self):
        bio = BesluitInformatieObjectFactory.create()
        bio_url = reverse(bio)

        response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        # Relation is gone, besluit still exists.
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertTrue(Besluit.objects.exists())


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse(BesluitInformatieObject)

    def test_create_bio_external_document(self):
        base = "https://external.documenten.nl/api/v1/"
        document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        besluit = BesluitFactory.create(besluittype__concept=False)
        besluit_url = f"http://openzaak.nl{reverse(besluit)}"
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=besluit.besluittype.catalogus, concept=False
        )
        informatieobjecttype_url = f"http://openzaak.nl{reverse(informatieobjecttype)}"
        informatieobjecttype.besluittypen.add(besluit.besluittype)
        eio_response = get_eio_response(document, informatieobjecttype=informatieobjecttype_url)

        with self.subTest(section="bio-create"):
            with requests_mock.Mocker(real_http=True) as m:
                m.get(document, json=eio_response)
                m.post(
                    "https://external.documenten.nl/api/v1/objectinformatieobjecten",
                    json=get_oio_response(document, besluit_url, "besluit"),
                    status_code=201,
                )

                response = self.client.post(
                    self.list_url,
                    {"besluit": besluit_url, "informatieobject": document},
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
                    "object": besluit_url,
                    "objectType": "besluit",
                },
            )

            self.assertFalse(ObjectInformatieObject.objects.exists())

        with self.subTest(section="bio-list"):
            list_response = self.client.get(
                self.list_url,
                {"besluit": besluit_url},
                HTTP_HOST="openzaak.nl",
            )

            self.assertEqual(list_response.status_code, status.HTTP_200_OK, response.data)
            data = list_response.json()

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["informatieobject"], document)

    def test_create_bio_fail_bad_url(self):
        besluit = BesluitFactory.create(besluittype__concept=False)
        besluit_url = f"http://openzaak.nl{reverse(besluit)}"
        data = {"besluit": besluit_url, "informatieobject": "abcd"}

        response = self.client.post(self.list_url, data, HTTP_HOST="openzaak.nl")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "bad-url")

    def test_create_bio_fail_not_json(self):
        besluit = BesluitFactory.create(besluittype__concept=False)
        besluit_url = f"http://openzaak.nl{reverse(besluit)}"
        data = {"besluit": besluit_url, "informatieobject": "http://example.com"}

        response = self.client.post(self.list_url, data, HTTP_HOST="openzaak.nl")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_bio_fail_invalid_schema(self):
        base = "https://external.documenten.nl/api/v1/"
        document = f"{base}enkelvoudiginformatieobjecten/{uuid.uuid4()}"
        besluit = BesluitFactory.create(besluittype__concept=False)
        besluit_url = f"http://openzaak.nl{reverse(besluit)}"
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=besluit.besluittype.catalogus, concept=False
        )
        informatieobjecttype_url = f"http://openzaak.nl{reverse(informatieobjecttype)}"
        informatieobjecttype.besluittypen.add(besluit.besluittype)

        with requests_mock.Mocker(real_http=True) as m:
            m.get(
                document,
                json={
                    "url": document,
                    "beschrijving": "",
                    "ontvangstdatum": None,
                    "informatieobjecttype": informatieobjecttype_url,
                    "locked": False,
                },
            )

            response = self.client.post(
                self.list_url,
                {"besluit": besluit_url, "informatieobject": document},
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid-resource")
