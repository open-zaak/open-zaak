# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class BesluitInformatieObjectCMISAPITests(JWTAuthMixin, APICMISTestCase, OioMixin):

    list_url = reverse_lazy("besluitinformatieobject-list", kwargs={"version": "1"})

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def test_create(self):
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()

        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        besluit_url = make_absolute_uri(reverse(besluit))
        content = {
            "informatieobject": io_url,
            "besluit": besluit_url,
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
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        BesluitInformatieObjectFactory.create(informatieobject=io_url, besluit=besluit)
        besluit_url = make_absolute_uri(reverse(besluit))

        content = {
            "informatieobject": io_url,
            "besluit": besluit_url,
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_read_besluit(self):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
        bio_detail_url = reverse(bio)

        response = self.client.get(bio_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        besluit_url = reverse(bio.besluit)
        expected = {
            "url": f"http://testserver{bio_detail_url}",
            "informatieobject": io_url,
            "besluit": f"http://testserver{besluit_url}",
        }

        self.assertEqual(response.json(), expected)

    def test_filter_by_besluit(self):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
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
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://openzaak.nl{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        BesluitInformatieObjectFactory.create(informatieobject=io_url, besluit=besluit)
        bio_list_url = reverse("besluitinformatieobject-list")

        response = self.client.get(
            bio_list_url, {"informatieobject": io_url}, HTTP_HOST="openzaak.nl",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], io_url)

    def test_put_besluit_not_allowed(self):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
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
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
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
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
        bio_url = reverse(bio)

        response = self.client.delete(bio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        # Relation is gone, besluit still exists.
        self.assertFalse(BesluitInformatieObject.objects.exists())
        self.assertTrue(Besluit.objects.exists())
