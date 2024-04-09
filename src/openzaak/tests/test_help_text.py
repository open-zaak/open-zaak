# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import TestCase

from openzaak.utils.help_text import mark_experimental


class HelptextTests(TestCase):
    def mark_experimental_test(self):
        marked_text = mark_experimental("lorem ipsum")

        self.assertContains(
            marked_text,
            "Warning: this feature is experimental and not part of the API standard",
        )
