# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Bootstrap the environment.

Load the secrets from the .env file and store them in the environment, so
they are available for Django settings initialization.

.. warning::

    do NOT import anything Django related here, as this file needs to be loaded
    before Django is initialized.
"""

import os
import re
import tempfile

from django.conf import settings

import structlog
from dotenv import load_dotenv
from self_certifi import load_self_signed_certs as _load_self_signed_certs

EXTRA_CERTS_ENVVAR = "EXTRA_VERIFY_CERTS"

logger = structlog.stdlib.get_logger(__name__)


def setup_env():
    # load the environment variables containing the secrets/config
    dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, ".env")
    load_dotenv(dotenv_path)

    structlog.contextvars.bind_contextvars(source="app")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openzaak.conf.dev")

    load_self_signed_certs()

    monkeypatch_drf_camel_case()

    monkeypatch_requests()


def load_self_signed_certs() -> None:
    """
    Load self-signed/private CA bundles in an idempotent manner.

    :func:`setup_env` is called multiple times in Celery setups. self-certifi
    works by setting the ``REQUESTS_CA_BUNDLE`` envvar and errors out if this envvar
    is already set (as it conflicts with the way it operates). If the setup function
    runs multiple times, the envvar set by self-certifi would trip self-certifi in the
    second run.

    The guard clauses here ensure that loading the self-signed certs is done only once.
    """
    needs_extra_verify_certs = os.environ.get(EXTRA_CERTS_ENVVAR)
    if not needs_extra_verify_certs:
        return

    _certs_initialized = bool(os.environ.get("REQUESTS_CA_BUNDLE"))
    if _certs_initialized:
        return

    # create target directory for resulting combined certificate file
    target_dir = tempfile.mkdtemp()
    _load_self_signed_certs(target_dir)


def monkeypatch_drf_camel_case() -> None:
    """
    Revert the camelize_re back to the old behaviour.

    drf-camel-case had a camelize_re that excluded numbers, which was used while the
    standard was created. When upgrading drf-camel-case, we had to revert this regex
    back to the old one to stay compliant with the schema from the standard.

    TODO: bring up this more correct camelizing issue for a 2.x version of the standard
    where breaking changes are allowed.

    One of the relevant commits:
    https://github.com/vbabiy/djangorestframework-camel-case/commit/f814bf32461d274e99bf4f24dcd6bac06056c8b2#
    """
    from djangorestframework_camel_case import util

    util.camelize_re = re.compile(r"[a-z]_[a-z]")

    def old_underscore_to_camel(match):
        return match.group()[0] + match.group()[2].upper()

    util.underscore_to_camel = old_underscore_to_camel


def monkeypatch_requests():
    """
    Add a default timeout for any requests calls.

    """
    try:
        from requests import Session
    except ModuleNotFoundError:
        logger.debug("Attempt to patch requests, but the library is not installed")
        return

    if hasattr(Session, "_original_request"):
        logger.debug(
            "Session is already patched OR has an ``_original_request`` attribute."
        )
        return

    Session._original_request = Session.request

    def new_request(self, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        return self._original_request(*args, **kwargs)

    Session.request = new_request
