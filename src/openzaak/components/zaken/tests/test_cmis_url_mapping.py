# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import os
from unittest import skipIf

from django.test import override_settings

from drc_cmis.models import UrlMapping
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis


@require_cmis
@freeze_time("2018-06-27 12:12:12")
@override_settings(
    CMIS_ENABLED=True,
    CMIS_URL_MAPPING_ENABLED=True,
)
@skipIf(os.getenv("CMIS_BINDING") != "WEBSERVICE", "WEBSERVICE binding specific tests")
class URLMappingZIOAPITests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_create_no_url_mapping(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        titel = "some titel"
        beschrijving = "some beschrijving"
        content = {
            "informatieobject": io_url,
            "zaak": f"http://testserver{zaak_url}",
            "titel": titel,
            "beschrijving": beschrijving,
            "aardRelatieWeergave": "bla",  # Should be ignored by the API
        }

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        # Send to the API
        response = self.client.post(
            reverse("zaakinformatieobject-list", kwargs={"version": "1"}), content
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
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()

        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        zio_url = reverse(zio)

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.delete(zio_url)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )
