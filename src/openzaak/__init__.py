# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
# defined before importing celery, which loads the settings that read the version
__version__ = "1.31.0"

from .celery import app as celery_app  # noqa: E402

__all__ = ("celery_app",)
__author__ = "Maykin"
__homepage__ = "https://github.com/open-zaak/open-zaak"
