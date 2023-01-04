# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from celery import Celery

from openzaak.setup import setup_env

setup_env()

app = Celery("openzaak")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
