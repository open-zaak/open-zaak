# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import copy
import uuid

from django.db import models
from django.urls import reverse
from django.utils.functional import classproperty
from django.utils.translation import gettext as _

from privates.fields import PrivateMediaFileField

from openzaak.utils import build_absolute_url


def clone_object(instance):
    cloned = copy.deepcopy(instance)  # don't alter original instance
    cloned.pk = None
    cloned._state.adding = True
    try:
        delattr(cloned, "_prefetched_objects_cache")
    except AttributeError:
        pass
    return cloned


class ImportStatusChoices(models.TextChoices):
    pending = "pending", _("Openstaand")
    active = "active", _("Actief")
    finished = "finished", _("Voltooid")
    error = "error", _("Onderbroken")

    @classproperty
    def visible_choices(cls):
        return {cls.pending, cls.active, cls.finished, cls.error}

    @classproperty
    def started_choices(cls):
        return {cls.pending, cls.active}

    @classproperty
    def report_choices(cls):
        return {cls.finished, cls.error}


class ImportTypeChoices(models.TextChoices):
    documents = "documenten", _("Enkelvoudige informatie objecten")


class Import(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    status = models.CharField(choices=ImportStatusChoices.choices, max_length=30)
    import_type = models.CharField(
        verbose_name=_("Type import"), choices=ImportTypeChoices.choices, max_length=30
    )

    import_file = PrivateMediaFileField(
        verbose_name=_("Import metadata bestand"),
        upload_to="import/import-files/",
        blank=True,
        null=True,
    )

    report_file = PrivateMediaFileField(
        verbose_name=_("Reportage bestand"),
        upload_to="import/report-files/",
        blank=True,
        null=True,
    )

    # statistics
    total = models.IntegerField(verbose_name=_("Totaal"))
    processed = models.IntegerField(verbose_name=_("Verwerkt"), default=0)
    processed_succesfully = models.IntegerField(
        verbose_name=_("Succesvol verwerkt"), default=0
    )
    processed_invalid = models.IntegerField(
        verbose_name=_("Niet succesvol verwerkt"), default=0
    )

    def __str__(self):
        return str(self.uuid)

    # TODO: retrieve API version from request if possible
    def get_upload_url(self, request=None):
        relative_url = reverse(
            "documenten-import:upload", kwargs=dict(uuid=self.uuid, version="1")
        )
        return build_absolute_url(relative_url, request=request)

    def get_status_url(self, request=None):
        relative_url = reverse(
            "documenten-import:status", kwargs=dict(uuid=self.uuid, version="1")
        )
        return build_absolute_url(relative_url, request=request)

    def get_report_url(self, request=None):
        relative_url = reverse(
            "documenten-import:report", kwargs=dict(uuid=self.uuid, version="1")
        )
        return build_absolute_url(relative_url, request=request)
