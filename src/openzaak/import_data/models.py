# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.functional import classproperty
from django.utils.translation import gettext as _

from privates.fields import PrivateMediaFileField
from vng_api_common.constants import ComponentTypes

from openzaak.utils import build_absolute_url


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

    @classproperty
    def deletion_choices(cls):
        return {cls.finished, cls.error, cls.pending}


class ImportRowResultChoices(models.TextChoices):
    imported = "imported", _("Geïmporteerd")
    not_imported = "not_imported", _("Niet geïmporteerd")


class ImportTypeChoices(models.TextChoices):
    documents = "documenten", _("Enkelvoudige informatie objecten")

    @classproperty
    def component_mapping(cls):
        return {
            cls.documents: ComponentTypes.drc,
        }

    @classmethod
    def get_component_from_choice(cls, choice):
        return cls.component_mapping[choice]


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

    comment = models.TextField(verbose_name=_("Opmerking"), blank=True)

    # date related fields
    created_on = models.DateTimeField(
        verbose_name=_("Aangemaakt op"), auto_now_add=True
    )

    started_on = models.DateTimeField(
        verbose_name=_("Gestart op"), blank=True, null=True
    )

    finished_on = models.DateTimeField(
        verbose_name=_("Voltooid op"), blank=True, null=True
    )

    # statistics
    total = models.PositiveIntegerField(verbose_name=_("Totaal"))
    processed = models.PositiveIntegerField(verbose_name=_("Verwerkt"), default=0)
    processed_successfully = models.PositiveIntegerField(
        verbose_name=_("Succesvol verwerkt"), default=0
    )
    processed_invalid = models.PositiveIntegerField(
        verbose_name=_("Niet succesvol verwerkt"), default=0
    )

    def __str__(self):
        return str(self.uuid)

    def get_upload_url(self, request=None):
        relative_url = reverse(
            "documenten-import:upload",
            kwargs=dict(
                uuid=self.uuid, version=settings.REST_FRAMEWORK["DEFAULT_VERSION"]
            ),
        )
        return build_absolute_url(relative_url, request=request)

    def get_status_url(self, request=None):
        relative_url = reverse(
            "documenten-import:status",
            kwargs=dict(
                uuid=self.uuid, version=settings.REST_FRAMEWORK["DEFAULT_VERSION"]
            ),
        )
        return build_absolute_url(relative_url, request=request)

    def get_report_url(self, request=None):
        relative_url = reverse(
            "documenten-import:report",
            kwargs=dict(
                uuid=self.uuid, version=settings.REST_FRAMEWORK["DEFAULT_VERSION"]
            ),
        )
        return build_absolute_url(relative_url, request=request)

    def get_batch_number(self, batch_size: int):
        return int(self.processed / batch_size) + 1 if self.processed else 1

    def get_remaining_batches(self, batch_size: int):
        if self.total < 1:
            return 0
        elif self.processed < 1:
            return self.total / batch_size

        return int((self.total / batch_size) - (self.processed / batch_size))
