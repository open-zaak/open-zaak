# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.test import TestCase

from maykin_2fa.test import disable_admin_mfa
from rest_framework.exceptions import ErrorDetail

from openzaak.components.catalogi.admin.utils import format_serializer_errors


@disable_admin_mfa()
class SerializerErrorFormatterTests(TestCase):
    def test_basic_errors(self):

        errors = {"field1": [ErrorDetail("Format must be valid", "invalidformat")]}

        self.assertEqual(
            format_serializer_errors(errors), "field1: Format Must Be Valid"
        )

    def test_basic_multiple_errors(self):

        errors = {
            "field1": [ErrorDetail("Format must be valid", "invalidformat")],
            "field2": [ErrorDetail("Field is required", "required")],
        }

        self.assertEqual(
            format_serializer_errors(errors),
            "field1: Format Must Be Valid\n" "field2: Field Is Required",
        )

    def test_nested_errors(self):
        errors = {
            "foreign_key_field": {
                "field1": [ErrorDetail("Format must be valid", "invalidformat")],
                "field2": [ErrorDetail("Field is required", "required")],
            }
        }

        self.assertEqual(
            format_serializer_errors(errors),
            "foreign_key_field: "
            "field1: Format Must Be Valid, "
            "field2: Field Is Required",
        )

    def test_double_nested_errors(self):
        errors = {
            "foreign_key_field": {
                "other_fk_field": {
                    "field2": [ErrorDetail("Field is required", "required")],
                }
            }
        }
        self.assertEqual(
            format_serializer_errors(errors),
            "foreign_key_field: other_fk_field: field2: Field Is Required",
        )

    def test_mixed_errors(self):
        errors = {
            "foreign_key_field": {
                "other_fk_field": {
                    "field2": [ErrorDetail("Field is required", "required")],
                }
            },
            "fk_field_2": {"field3": [ErrorDetail("Field is required", "required")]},
            "regular_field": [ErrorDetail("Format must be valid", "invalidformat")],
        }

        self.assertEqual(
            format_serializer_errors(errors),
            "foreign_key_field: other_fk_field: field2: Field Is Required\n"
            "fk_field_2: field3: Field Is Required\n"
            "regular_field: Format Must Be Valid",
        )
