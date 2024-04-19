# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import unittest

from openzaak.utils.help_text import mark_experimental


class HelptextTests(unittest.TestCase):
    def test_mark_experimental(self):
        marked_text = mark_experimental("lorem ipsum")

        self.assertEqual(marked_text, "**EXPERIMENTEEL** lorem ipsum")
