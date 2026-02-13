# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from contextlib import contextmanager
from typing import Generator

import structlog
from structlog import configure, get_config
from structlog.testing import LogCapture
from structlog.typing import EventDict


@contextmanager
def capture_logs() -> Generator[list[EventDict], None, None]:
    """
    NOTE: Taken from `structlog.testing.capture_logs`, this also adds the
    `merge_contextvars` processor to make sure contextvars are captured as well

    Context manager that appends all logging statements to its yielded list
    while it is active. Disables all configured processors for the duration
    of the context manager.

    Attention: this is **not** thread-safe!

    .. versionadded:: 20.1.0
    """
    cap = LogCapture()
    # Modify `_Configuration.default_processors` set via `configure` but always
    # keep the list instance intact to not break references held by bound
    # loggers.
    processors = get_config()["processors"]
    old_processors = processors.copy()
    try:
        # clear processors list and use LogCapture for testing
        processors.clear()
        # Make sure contextvars are also added
        processors.extend([structlog.contextvars.merge_contextvars, cap])
        configure(processors=processors)
        yield cap.entries
    finally:
        # remove LogCapture and restore original processors
        processors.clear()
        processors.extend(old_processors)
        configure(processors=processors)
