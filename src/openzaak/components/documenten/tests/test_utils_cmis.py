# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.utils.convert import make_absolute_uri
from rest_framework.reverse import reverse_lazy
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.documenten.query.cmis import get_related_data_for_oio_create
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.components.zaken.tests.utils import get_zaak_response
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis


@tag("external-urls")
@require_cmis
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class CMISUtilsTests(JWTAuthMixin, APICMISTestCase):

    list_url = reverse_lazy(ZaakInformatieObject)
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def test_get_zaak_and_zaaktype_data(self):
        zaak = ZaakFactory.create()
        zaak_url = make_absolute_uri(reverse(zaak))

        zaak_data, zaaktype_data, _ = get_related_data_for_oio_create("zaak", zaak_url)

        expected_zaak_fields = ["url", "identificatie", "bronorganisatie", "zaaktype"]
        expected_zaaktype_fields = ["url", "identificatie", "omschrijving"]

        for field in expected_zaak_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaak_data)

        for field in expected_zaaktype_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaaktype_data)

    def test_get_zaak_and_zaaktype_data_related_to_besluit(self):
        zaak = ZaakFactory.create()
        BesluitFactory.create(zaak=zaak)
        zaak_url = make_absolute_uri(reverse(zaak))

        zaak_data, zaaktype_data, _ = get_related_data_for_oio_create("zaak", zaak_url)

        expected_zaak_fields = ["url", "identificatie", "bronorganisatie", "zaaktype"]
        expected_zaaktype_fields = ["url", "identificatie", "omschrijving"]

        for field in expected_zaak_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaak_data)

        for field in expected_zaaktype_fields:
            with self.subTest(field=field):
                self.assertIn(field, zaaktype_data)

    def test_format_external_zaak(self):
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/", api_type=APITypes.ztc
        )
        zaak = "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"

        self.adapter.get(zaak, json=get_zaak_response(zaak, zaaktype))
        self.adapter.get(zaaktype, json=get_zaak_response(catalogus, zaaktype))

        zaak_data, zaaktype_data, _ = get_related_data_for_oio_create("zaak", zaak)

        self.assertEqual(zaak_data["url"], zaak)
        self.assertEqual(zaak_data["zaaktype"], zaaktype)
        self.assertEqual(zaaktype_data["url"], zaaktype)
