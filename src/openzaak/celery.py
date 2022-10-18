from celery import Celery

from openzaak.setup import setup_env

setup_env()

app = Celery("openzaak")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
