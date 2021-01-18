# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
WSGI config for zrc project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""
import os

from django.core.wsgi import get_wsgi_application

from openzaak.setup import setup_env


def init_newrelic():
    if os.environ.get("PROJECT_ROOT"):
        try:
            import newrelic.agent

            newrelic.agent.initialize(
                os.path.join(os.environ.get("PROJECT_ROOT"), "newrelic.ini"),
                "production",
            )
        except Exception as e:
            print("Could not initialize New Relic APM, ignoring:")
            print(e)


# Enable New Relic on production
# init_newrelic()

setup_env()
application = get_wsgi_application()
