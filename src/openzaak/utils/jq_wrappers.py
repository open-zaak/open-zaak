# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
"""
Wrappers for `jq`

We wrap `jq` with `subprocess.run` with an explicit timeout, because executing user
supplied jq expressions can lead to high resource consumption and potentially DoS.

Additionally, when running `jq` via the python library, it always has access to
all environment variables, which for the purpose that jq is used for in Open Zaak
is not necessary at all.

Ideally, we would move away from `jq` entirely and use something simpler (e.g. JSONpath, JMESpath),
because for the use case in Open Zaak, `jq` is overkill.
"""

import json
import subprocess
from shutil import which

from .typing import JSONValue

_MAX_INPUT_BYTES = 4 * 1024 * 1024  # 4 MiB
_MAX_EXPRESSION_BYTES = 64 * 1024  # 64 KiB


class JQExecutionError(Exception):
    pass


class JQInvalidExpressionError(JQExecutionError):
    """The supplied expression is not valid jq."""


def validate_jq(expression: str, timeout: float = 1) -> None:
    """
    Validate that expression is valid jq.

    Raises:
        JQInvalidExpressionError: If the expression is not valid jq.
        JQExecutionError: If jq cannot be executed or times out.
    """
    if len(expression.encode("utf-8")) > _MAX_EXPRESSION_BYTES:
        raise JQInvalidExpressionError("jq expression is too large")

    jq_binary_path = which("jq")
    assert jq_binary_path, "jq binary not installed!"

    try:
        result = subprocess.run(
            [jq_binary_path, "-c", expression],
            input="null",
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,  # to avoid shell injection
            env={},  # Isolate the env to not give access to all envvars
        )
    except subprocess.TimeoutExpired as exc:
        raise JQExecutionError("jq expression validation timed out") from exc
    except OSError as exc:
        raise JQExecutionError("could not execute jq") from exc

    if result.returncode != 0:
        raise JQInvalidExpressionError(f"invalid jq expression: {result.stderr[:4000]}")


def get_first_jq_result(
    expression: str, input_json: bytes, timeout: float = 1
) -> JSONValue:
    """
    Execute a jq expression against data and return the first result.

    This is run via `subprocess` with an explicit timeout, because executing user
    supplied jq expressions can lead to high resource consumption and potentially DoS.

    Additionally, when running `jq` via the python library, it always has access to
    all environment variables, which for the purpose that jq is used for in Open Zaak
    is not necessary at all.

    Raises:
        JQExecutionError: If jq cannot be executed successfully.
    """
    if len(expression.encode("utf-8")) > _MAX_EXPRESSION_BYTES:
        raise JQInvalidExpressionError("jq expression is too large")

    if len(input_json) > _MAX_INPUT_BYTES:
        raise JQExecutionError("jq input is too large")

    jq_binary_path = which("jq")
    assert jq_binary_path, "jq binary not installed!"

    try:
        result = subprocess.run(
            [jq_binary_path, "-c", f"[{expression}][0]"],
            input=input_json,
            text=False,
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,  # to avoid shell injection
            env={},  # Isolate the env to not give access to all envvars
        )
    except subprocess.TimeoutExpired as exc:
        raise JQExecutionError("jq execution timed out") from exc
    except OSError as exc:
        raise JQExecutionError("could not execute jq") from exc

    if result.returncode != 0:
        raise JQExecutionError(f"jq failed: {result.stderr[:4000]}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise JQExecutionError("jq returned invalid JSON") from exc
