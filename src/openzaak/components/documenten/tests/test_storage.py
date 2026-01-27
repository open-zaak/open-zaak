# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import os
from importlib import reload
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

import openzaak.conf.includes.base
from openzaak.components.documenten.exceptions import DocumentBackendNotImplementedError

from ..storage import documenten_storage


class DocumentenAPIStorageTestCase(SimpleTestCase):
    def test_incorrect_storage_raises_error(self):
        with patch.dict(os.environ, {"DOCUMENTEN_API_BACKEND": "invalid"}):
            with self.assertRaises(ValueError) as cm:
                reload(openzaak.conf.includes.base)

            self.assertEqual(
                str(cm.exception), "'invalid' is not a valid DocumentenBackendTypes"
            )

    @override_settings(DOCUMENTEN_API_BACKEND="test")
    def test_not_implemented_documenten_api_backend(self):
        with self.assertRaises(DocumentBackendNotImplementedError):
            documenten_storage._setup()
