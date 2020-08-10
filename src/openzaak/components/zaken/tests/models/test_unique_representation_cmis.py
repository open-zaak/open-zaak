# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, OioMixin, serialise_eio

from ..factories import ZaakInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class UniqueRepresentationCMISTestCase(APICMISTestCase, OioMixin):
    def test_zaakinformatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create(identificatie="12345")
        eio_url = eio.get_url()
        self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(
            **{
                "bronorganisatie": 730924658,
                "identificatie": "5d940d52-ff5e-4b18-a769-977af9130c04",
            }
        )
        zio = ZaakInformatieObjectFactory(zaak=zaak, informatieobject=eio_url,)

        self.assertEqual(
            zio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
