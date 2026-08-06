import json
from unittest.mock import patch

from django.test import SimpleTestCase

from openzaak.utils.jq_wrappers import (
    _MAX_EXPRESSION_BYTES,
    _MAX_INPUT_BYTES,
    JQExecutionError,
    JQInvalidExpressionError,
    get_first_jq_result,
    validate_jq,
)


class JQWrappersTestCase(SimpleTestCase):
    def test_validate_jq_success(self):
        validate_jq(".foo")

    def test_validate_jq_invalid_expression(self):
        with self.assertRaises(JQInvalidExpressionError):
            validate_jq(".foo |")

    @patch("openzaak.utils.jq_wrappers.subprocess.run")
    def test_validate_jq_raises_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["/usr/bin/jq", "-c", ".foo"],
            timeout=2,
        )

        with self.assertRaisesMessage(
            JQExecutionError,
            "jq expression validation timed out",
        ):
            validate_jq(".foo")

    def test_validate_jq_max_expression_bytes(self):
        expression = "a" * (_MAX_EXPRESSION_BYTES + 1)

        with self.assertRaisesMessage(
            JQInvalidExpressionError,
            "jq expression is too large",
        ):
            validate_jq(expression)

    def test_run_jq_success(self):
        result = get_first_jq_result(
            ".foo",
            b'{"foo": "bar"}',
        )

        self.assertEqual(result, "bar")

    def test_run_jq_invalid_json(self):
        with self.assertRaises(
            JQExecutionError,
        ) as cm:
            get_first_jq_result(
                ".foo",
                b'"foo": "bar"}',
            )

        self.assertTrue(
            str(cm.exception).startswith(
                "jq failed: b'jq: error (at <stdin>:0): Cannot index string with string"
            )
        )

    def test_run_jq_cannot_access_environment_variables(self):
        result = get_first_jq_result(
            '{"const": env.SECRET_KEY}',
            b"{}",
        )

        self.assertEqual(result, {"const": None})

    @patch("openzaak.utils.jq_wrappers.subprocess.run")
    def test_run_jq_raises_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["/usr/bin/jq", "-c", ".foo"],
            timeout=2,
        )

        with self.assertRaisesMessage(
            JQExecutionError,
            "jq execution timed out",
        ):
            get_first_jq_result(".foo", b'{"foo": "bar"}')

    def test_run_jq_max_expression_bytes(self):
        expression = "a" * (_MAX_EXPRESSION_BYTES + 1)

        with self.assertRaisesMessage(
            JQInvalidExpressionError,
            "jq expression is too large",
        ):
            get_first_jq_result(expression, b'{"foo": "bar"}')

    def test_run_jq_max_input_bytes(self):
        # Make sure the serialized JSON exceeds the configured limit.
        data = json.dumps({"value": "a" * _MAX_INPUT_BYTES}).encode("utf-8")

        with self.assertRaisesMessage(
            JQExecutionError,
            "jq input is too large",
        ):
            get_first_jq_result(".", data)

    def test_run_jq_only_returns_first_result(self):
        result = get_first_jq_result(
            "range(0; 3)",
            b"{}",
            timeout=1,
        )

        self.assertEqual(result, 0)
