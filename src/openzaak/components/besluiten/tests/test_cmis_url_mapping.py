# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import os
from unittest import skipIf

from django.test import override_settings, tag

from drc_cmis.models import UrlMapping
from drc_cmis.utils.convert import make_absolute_uri
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.besluiten.tests.factories import BesluitInformatieObjectFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio


@tag("cmis")
@freeze_time("2018-06-27 12:12:12")
@override_settings(
    CMIS_ENABLED=True, CMIS_URL_MAPPING_ENABLED=True,
)
@skipIf(os.getenv("CMIS_BINDING") != "WEBSERVICE", "WEBSERVICE binding specific tests")
class URLMappingBIOAPITests(JWTAuthMixin, APICMISTestCase, OioMixin):

    heeft_alle_autorisaties = True

    def test_create_no_url_mapping(self):
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

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        # Send to the API
        response = self.client.post(
            reverse("besluitinformatieobject-list", kwargs={"version": "1"}), content
        )

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_delete_no_url_mapping(self):
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        bio = BesluitInformatieObjectFactory.create(
            informatieobject=io_url, besluit=besluit
        )
        bio_url = reverse(bio)

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.delete(bio_url)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )
