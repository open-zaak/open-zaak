# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
WSGI config for zrc project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""
from django.core.wsgi import get_wsgi_application

from openzaak.setup import setup_env

setup_env()
application = get_wsgi_application()
