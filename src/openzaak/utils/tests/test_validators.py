# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.translation import gettext as _

from rest_framework import serializers

from openzaak.utils.jq_wrappers import JQExecutionError, JQInvalidExpressionError
from openzaak.utils.validators import JQExpressionValidator


class JQExpressionValidatorTests(SimpleTestCase):
    @patch("openzaak.utils.validators.validate_jq")
    def test_valid_expression(self, mock_validate_jq):
        validator = JQExpressionValidator()

        result = validator(".foo")

        self.assertIsNone(result)
        mock_validate_jq.assert_called_once_with(".foo")

    @patch(
        "openzaak.utils.validators.validate_jq",
        side_effect=JQInvalidExpressionError("invalid jq expression"),
    )
    def test_invalid_expression(self, mock_validate_jq):
        validator = JQExpressionValidator()

        with self.assertRaises(serializers.ValidationError) as context:
            validator(".foo |")

        self.assertEqual(
            context.exception.detail[0].code,
            "invalid",
        )
        self.assertEqual(
            str(context.exception.detail[0]),
            validator.message,
        )
        mock_validate_jq.assert_called_once_with(".foo |")

    @patch(
        "openzaak.utils.validators.validate_jq",
        side_effect=JQExecutionError("jq execution timed out"),
    )
    def test_jq_execution_error(self, mock_validate_jq):
        validator = JQExpressionValidator()

        with self.assertRaises(serializers.ValidationError) as context:
            validator(".foo")

        self.assertEqual(
            context.exception.detail[0].code,
            "invalid",
        )
        self.assertEqual(
            str(context.exception.detail[0]),
            _("An error occurred while executing the jq expression."),
        )
        mock_validate_jq.assert_called_once_with(".foo")
