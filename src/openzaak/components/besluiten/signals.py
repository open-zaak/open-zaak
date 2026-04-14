# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

import structlog
from django_loose_fk.virtual_models import ProxyMixin

from openzaak.components.besluiten.models import Besluit
from openzaak.components.zaken.signals import schedule_zaak_gemuteerd

logger = structlog.stdlib.get_logger(__name__)


@receiver(
    post_save,
    sender=Besluit,
    dispatch_uid="besluiten.besluit.send_zaak_gemuteerd_event",
)
def send_besluit_zaak_gemuteerd_event(sender, instance, created, **kwargs):
    if kwargs.get("update_fields") in (frozenset({"_etag"}),):
        return

    if zaak := instance.zaak:
        if isinstance(zaak, ProxyMixin):
            return

        zaak = instance.zaak
        zaak.laatst_gemuteerd = timezone.now()
        zaak.save(update_fields=["laatst_gemuteerd"])

        schedule_zaak_gemuteerd(zaak)


@receiver(
    pre_delete,
    sender=Besluit,
    dispatch_uid="besluiten.besluit.delete.send_zaak_gemuteerd_event",
)
def send_besluit_deleted_gemuteerd_event(sender, instance, **kwargs):
    if kwargs.get("update_fields") in (frozenset({"_etag"}),):
        return

    if zaak := instance.zaak:
        if isinstance(zaak, ProxyMixin):
            return

        zaak = instance.zaak
        zaak.laatst_gemuteerd = timezone.now()
        zaak.save(update_fields=["laatst_gemuteerd"])

        schedule_zaak_gemuteerd(zaak)
