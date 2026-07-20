# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from ..setup import setup_env

setup_env()

from .app import app  # noqa: E402

__all__ = ("app",)
