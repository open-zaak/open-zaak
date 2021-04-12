# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.core.exceptions import ValidationError
from django.test import TestCase

from ..factories import CatalogusFactory, InformatieObjectTypeFactory


class InformatieobjecttypeValidationTests(TestCase):
    """
    Test the validation on Informatieobjecttype
    """

    def test_assertion_raised_when_dates_overlap(self):
        catalogus = CatalogusFactory.create()

        InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
        )

        instance = InformatieObjectTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-10-10",
        )

        with self.assertRaises(ValidationError):
            instance.clean()
