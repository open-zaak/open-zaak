# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from base64 import b64encode

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.besluiten.models import Besluit
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.zaken.models import Zaak
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from openzaak.utils.tests import JWTAuthMixin

from ..models import FeatureFlags


class ConceptFeatureFlagTests(JWTAuthMixin, APITestCase):
    """
    Test the feature flags that bypass FOO.concept validation.
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        feature_flags = FeatureFlags.get_solo()
        feature_flags.allow_unpublished_typen = True
        feature_flags.save()

    def test_zaak_create(self):
        """
        Assert that it's possible to create a zaak with an unpublished zaaktype when
        the feature flag is set.
        """
        zaaktype = ZaakTypeFactory.create(concept=True)
        zaaktype_url = reverse(zaaktype)
        url = reverse(Zaak)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "123456782",
            "verantwoordelijkeOrganisatie": "123456782",
            "startdatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_informatieobject_create(self):
        eio_url = reverse(EnkelvoudigInformatieObject)
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(eio_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_besluit_create(self):
        besluit_url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=True)
        besluittype_url = reverse(besluittype)

        data = {
            "verantwoordelijke_organisatie": "517439943",
            "besluittype": f"http://testserver{besluittype_url}",
            "datum": "2018-09-06",
            "ingangsdatum": "2018-10-01",
        }

        response = self.client.post(besluit_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
