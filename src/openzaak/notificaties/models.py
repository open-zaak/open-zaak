from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.timezone import now


class FailedNotification(models.Model):
    status_code = models.PositiveIntegerField()
    app = models.CharField(max_length=20, blank=True)
    model = models.CharField(max_length=30, blank=True)
    data = JSONField(encoder=DjangoJSONEncoder, null=True)
    instance = JSONField(encoder=DjangoJSONEncoder, null=True)
    exception = models.CharField(max_length=2000)
    timestamp = models.DateTimeField(default=now)
