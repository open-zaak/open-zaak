# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import mock_service_oas_get
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, serialise_eio

from ..models import Zaak, ZaakInformatieObject
from .utils import ZAAK_WRITE_KWARGS


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

    def _create_zaak(self, **headers):
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
        mock_service_oas_get(self.adapter, APITypes.zrc, base_zaak)
        mock_service_oas_get(self.adapter, APITypes.ztc, base_zaaktype)

        url = reverse(Zaak)
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaak_data = {
            "zaaktype": zaaktype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-12-24",
            "startdatum": "2018-12-24",
            "productenOfDiensten": ["https://example.com/product/123"],
        }

        response = self.client.post(url, zaak_data, **ZAAK_WRITE_KWARGS, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Mocking calls for the CMIS adapter, for when it will create a Oio
        zaak = Zaak.objects.get()
        zaak_url = f"http://testserver{reverse(zaak)}"

        self.adapter.get(
            zaak_url,
            json={
                "url": zaak_url,
                "identificatie": zaak.identificatie,
                "zaaktype": zaaktype_url,
            },
        )
        self.adapter.get(
            zaaktype_url,
            json={
                "url": zaaktype_url,
                "identificatie": zaak.zaaktype.identificatie,
                "omschrijving": "Melding Openbare Ruimte",
            },
        )

        return response.data

    def test_create_zaakinformatieobject_audittrail(self):
        zaak_data = self._create_zaak()
        zaak = Zaak.objects.get()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url, {"zaak": zaak_data["url"], "informatieobject": io_url,},
        )
        zaakinformatieobject_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=zaak_data["url"]).order_by(
            "pk"
        )
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the ZaakInformatieObject creation
        # contains the correct information
        zio_create_audittrail = audittrails[1]
        self.assertEqual(zio_create_audittrail.bron, "ZRC")
        self.assertEqual(zio_create_audittrail.actie, "create")
        self.assertEqual(zio_create_audittrail.resultaat, 201)
        self.assertEqual(zio_create_audittrail.oud, None)
        self.assertEqual(zio_create_audittrail.nieuw, zaakinformatieobject_response)
