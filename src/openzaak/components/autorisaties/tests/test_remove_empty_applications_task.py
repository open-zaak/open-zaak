# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase

from openzaak.components.autorisaties.models import Applicatie
from openzaak.components.autorisaties.tasks import remove_empty_applications
from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    AutorisatieFactory,
    CatalogusAutorisatieFactory,
)


class TestRemoveEmptyApplicationsTask(TestCase):
    def test_empty_application_are_removed(self):
        # to be removed
        empty = ApplicatieFactory.create(heeft_alle_autorisaties=False)

        # kept because of `heeft_alle_autorisaties`
        ApplicatieFactory.create(heeft_alle_autorisaties=True)

        # kept because of catalogi autorisatie
        cat_app = ApplicatieFactory.create(heeft_alle_autorisaties=False)
        CatalogusAutorisatieFactory.create(applicatie=cat_app)

        # kept because of autorisatie
        app = ApplicatieFactory.create(heeft_alle_autorisaties=False)
        AutorisatieFactory.create(applicatie=app)

        self.assertEqual(Applicatie.objects.count(), 4)

        remove_empty_applications()

        self.assertEqual(Applicatie.objects.count(), 3)

        with self.assertRaises(Applicatie.DoesNotExist):
            empty.refresh_from_db()
