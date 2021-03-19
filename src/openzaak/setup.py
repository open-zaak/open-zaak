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
import shutil
import tempfile

import certifi
from dotenv import load_dotenv

EXTRA_CERTS_ENVVAR = "EXTRA_VERIFY_CERTS"


def setup_env():
    # load the environment variables containing the secrets/config
    dotenv_path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, ".env")
    load_dotenv(dotenv_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openzaak.conf.dev")

    load_self_signed_certs()


def load_self_signed_certs() -> None:
    paths = os.environ.get(EXTRA_CERTS_ENVVAR, "")
    if not paths:
        return

    if "REQUESTS_CA_BUNDLE" in os.environ:
        raise ValueError(
            f"'{EXTRA_CERTS_ENVVAR}' and 'REQUESTS_CA_BUNDLE' conflict with each other."
        )

    # create target directory for resulting combined certificate file
    target_dir = tempfile.mkdtemp()

    # collect all extra certificates
    certs = []
    for path in paths.split(","):
        with open(path, "r") as certfile:
            certs.append(certfile.read())

    # copy certifi bundle to target_dir
    source = certifi.where()
    target = os.path.join(target_dir, os.path.basename(source))
    shutil.copy(source, target)

    with open(target, "a") as outfile:
        outfile.write("\n# Extra (self-signed) trusted certificates\n")
        outfile.write("\n\n".join(certs))

    # finally, set the REQUESTS_CA_BUNDLE environment variable
    os.environ["REQUESTS_CA_BUNDLE"] = target
