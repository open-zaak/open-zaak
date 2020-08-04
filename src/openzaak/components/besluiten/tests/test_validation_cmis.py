# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, serialise_eio

from .factories import BesluitFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class BesluitInformatieObjectCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_validate_no_informatieobjecttype_besluittype_relation(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        besluit_url = reverse(besluit)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = reverse(io)
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

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
