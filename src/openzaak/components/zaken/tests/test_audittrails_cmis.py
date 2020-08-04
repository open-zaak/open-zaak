# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ...documenten.tests.utils import serialise_eio
from ..models import Zaak, ZaakInformatieObject
from .utils import ZAAK_WRITE_KWARGS


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class AuditTrailCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def _create_zaak(self, **headers):
        url = reverse(Zaak)
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        zaak_data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-12-24",
            "startdatum": "2018-12-24",
            "productenOfDiensten": ["https://example.com/product/123"],
        }
        response = self.client.post(url, zaak_data, **ZAAK_WRITE_KWARGS, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
