# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import mock_service_oas_get
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, serialise_eio

from ...zaken.tests.factories import ZaakFactory
from ..models import Besluit, BesluitInformatieObject


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class AuditTrailCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def _create_besluit(self, **HEADERS):
        base_besluit = "http://testserver/besluiten/api/v1/"
        base_zaak = "http://testserver/zaken/api/v1/"
        base_zaaktype = "http://testserver/catalogi/api/v1/"

        Service.objects.create(
            api_type=APITypes.zrc,
            api_root=base_zaak,
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )
        Service.objects.create(
            api_type=APITypes.ztc,
            api_root=base_zaaktype,
            label="external zaaktypen",
            auth_type=AuthTypes.no_auth,
        )
        Service.objects.create(
            api_type=APITypes.brc,
            api_root=base_besluit,
            label="external besluiten",
            auth_type=AuthTypes.no_auth,
        )
        mock_service_oas_get(self.adapter, APITypes.zrc, base_zaak)
        mock_service_oas_get(self.adapter, APITypes.ztc, base_zaaktype)
        mock_service_oas_get(self.adapter, APITypes.brc, base_besluit)

        zaak = ZaakFactory.create(zaaktype__concept=False)

        url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        besluittype.zaaktypen.add(zaak.zaaktype)

        besluit_data = {
            "verantwoordelijkeOrganisatie": "000000000",
            "besluittype": f"http://testserver{besluittype_url}",
            "datum": "2019-04-25",
            "ingangsdatum": "2019-04-26",
            "vervaldatum": "2019-04-28",
            "identificatie": "123123",
            "zaak": f"http://testserver{reverse(zaak)}",
        }
        response = self.client.post(url, besluit_data, **HEADERS)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Mocking calls for the CMIS adapter, for when it will create a Oio
        besluit = Besluit.objects.get()
        zaak_url = f"http://testserver{reverse(besluit.zaak)}"
        zaaktype_url = f"http://testserver{reverse(besluit.zaak.zaaktype)}"
        besluit_url = f"http://testserver{reverse(besluit)}"

        self.adapter.get(
            zaak_url,
            json={
                "url": zaak_url,
                "identificatie": besluit.zaak.identificatie,
                "zaaktype": zaaktype_url,
            },
        )
        self.adapter.get(
            zaaktype_url,
            json={
                "url": zaaktype_url,
                "identificatie": besluit.zaak.zaaktype.identificatie,
                "omschrijving": "Melding Openbare Ruimte",
            },
        )
        self.adapter.get(besluit_url, json={"zaak": zaak_url})

        return response.data

    def test_create_besluitinformatieobject_audittrail(self):
        besluit_data = self._create_besluit()

        besluit = Besluit.objects.get()

        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        eio_url = f"http://testserver{reverse(eio)}"
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        besluit.besluittype.informatieobjecttypen.add(eio.informatieobjecttype)
        url = reverse(BesluitInformatieObject)

        response = self.client.post(
            url, {"besluit": besluit_data["url"], "informatieobject": eio_url,},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        besluitinformatieobject_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_data["url"])
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the BesluitInformatieObject creation
        # contains the correct information
        bio_create_audittrail = audittrails[1]
        self.assertEqual(bio_create_audittrail.bron, "BRC")
        self.assertEqual(bio_create_audittrail.actie, "create")
        self.assertEqual(bio_create_audittrail.resultaat, 201)
        self.assertEqual(bio_create_audittrail.oud, None)
        self.assertEqual(bio_create_audittrail.nieuw, besluitinformatieobject_response)
