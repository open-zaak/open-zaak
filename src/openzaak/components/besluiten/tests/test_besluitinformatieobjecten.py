from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import JWTAuthMixin

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
