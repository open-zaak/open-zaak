from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
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
