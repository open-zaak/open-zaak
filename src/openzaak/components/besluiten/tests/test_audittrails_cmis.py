# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, serialise_eio

from ..models import Besluit, BesluitInformatieObject


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class AuditTrailCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def _create_besluit(self, **HEADERS):
        url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        besluit_data = {
            "verantwoordelijkeOrganisatie": "000000000",
            "besluittype": f"http://testserver{besluittype_url}",
            "datum": "2019-04-25",
            "ingangsdatum": "2019-04-26",
            "vervaldatum": "2019-04-28",
            "identificatie": "123123",
        }
        response = self.client.post(url, besluit_data, **HEADERS)

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
