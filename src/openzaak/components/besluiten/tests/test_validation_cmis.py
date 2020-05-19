from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from .factories import BesluitFactory
from .utils import serialise_eio


@override_settings(CMIS_ENABLED=True)
class BesluitInformatieObjectCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_validate_informatieobject_invalid(self):
        besluit = BesluitFactory.create()
        besluit_url = reverse("besluit-detail", kwargs={"uuid": besluit.uuid})
        url = reverse("besluitinformatieobject-list")

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": "https://foo.bar/123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "bad-url")

    def test_validate_no_informatieobjecttype_besluittype_relation(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        besluit_url = reverse(besluit)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)
        self.adapter.register_uri("GET", io_url, json=serialise_eio(io, io_url))

        url = reverse("besluitinformatieobject-list")

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{besluit_url}",
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-besluittype-informatieobjecttype-relation"
        )
