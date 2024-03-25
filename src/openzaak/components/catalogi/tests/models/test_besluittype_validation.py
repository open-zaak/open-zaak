# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.core.exceptions import ValidationError
from django.test import TestCase

from ...models import BesluitType
from ..factories import BesluitTypeFactory, CatalogusFactory


class BesluitTypeValidationTests(TestCase):
    """
    Test the validation on BesluitType
    """

    def test_assertion_raised_when_dates_overlap(self):
        catalogus = CatalogusFactory.create()

        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
            concept=False,
        )

        instance = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-10-10",
            concept=False,
        )

        with self.assertRaises(ValidationError):
            instance.clean()

    def test_assertion_not_raised_when_concept_dates_overlap(self):
        catalogus = CatalogusFactory.create()

        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
            concept=False,
        )

        instance = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-10-10",
            concept=True,
        )
        instance.clean()
        self.assertEqual(BesluitType.objects.all().count(), 2)

    def test_assertion_not_raised_when_concept_dates_overlap_reverse(self):
        catalogus = CatalogusFactory.create()

        BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
            concept=True,
        )

        instance = BesluitTypeFactory.create(
            catalogus=catalogus,
            omschrijving="test",
            datum_begin_geldigheid="2018-10-10",
            concept=False,
        )
        instance.clean()
        self.assertEqual(BesluitType.objects.all().count(), 2)
