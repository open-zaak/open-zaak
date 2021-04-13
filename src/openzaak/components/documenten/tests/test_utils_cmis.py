# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from rest_framework.reverse import reverse_lazy
from vng_api_common.tests import reverse

from openzaak.components.documenten.query.cmis import get_zaak_and_zaaktype_data
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class CMISUtilsTests(JWTAuthMixin, APICMISTestCase, OioMixin):

    list_url = reverse_lazy(ZaakInformatieObject)
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def test_get_zaak_and_zaaktype_data(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        zaak_url = make_absolute_uri(reverse(zaak))

        zaak_data, zaaktype_data = get_zaak_and_zaaktype_data(zaak_url)

        expected_zaak_fields = ["url", "identificatie", "bronorganisatie", "zaaktype"]
        expected_zaaktype_fields = ["url", "identificatie", "omschrijving"]

        for field in expected_zaak_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaak_data)

        for field in expected_zaaktype_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaaktype_data)

    def test_get_zaak_and_zaaktype_data_related_to_besluit(self):
        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        zaak_url = make_absolute_uri(reverse(besluit.zaak))

        zaak_data, zaaktype_data = get_zaak_and_zaaktype_data(zaak_url)

        expected_zaak_fields = ["url", "identificatie", "bronorganisatie", "zaaktype"]
        expected_zaaktype_fields = ["url", "identificatie", "omschrijving"]

        for field in expected_zaak_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaak_data)

        for field in expected_zaaktype_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaaktype_data)
