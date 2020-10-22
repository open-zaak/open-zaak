# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase

from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding

from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    AutorisatieFactory,
    AutorisatieSpecFactory,
)
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils import build_absolute_url


class DeleteAutorisatieTest(TestCase):
    def test_autorisaties_are_deleted(self):
        applicatie = ApplicatieFactory.create()
        zaaktype = ZaakTypeFactory.create()
        AutorisatieFactory.create(
            applicatie=applicatie,
            component=ComponentTypes.zrc,
            zaaktype=build_absolute_url(zaaktype.get_absolute_api_url()),
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # Different max_vertrouwelijkheidaanduiding compared to the Autorisatie
        autorisatie_spec = AutorisatieSpecFactory.create(
            applicatie=applicatie,
            component=ComponentTypes.zrc,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        self.assertEqual(Autorisatie.objects.all().count(), 1)
        autorisatie = Autorisatie.objects.get()
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.openbaar,
        )

        autorisatie_spec.sync()

        # Check that the autorisatie that doesn't match the AutorisatieSpec is deleted and replaced with a correct one
        self.assertEqual(Autorisatie.objects.all().count(), 1)
        autorisatie = Autorisatie.objects.get()
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.geheim,
        )
