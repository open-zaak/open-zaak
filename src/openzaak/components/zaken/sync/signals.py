import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject

logger = logging.getLogger(__name__)


def sync_create_zio(relation: ZaakInformatieObject):
    ObjectInformatieObject.objects.create(
        zaak=relation.zaak,
        informatieobject=relation.informatieobject,
        object_type="zaak",
    )


def sync_delete_zio(relation: ZaakInformatieObject):
    ObjectInformatieObject.objects.filter(
        zaak=relation.zaak,
        informatieobject=relation.informatieobject,
        object_type="zaak",
    ).delete()


@receiver([post_save, post_delete], sender=ZaakInformatieObject)
def sync_informatieobject_relation(
    sender, instance: ZaakInformatieObject = None, **kwargs
):
    signal = kwargs["signal"]
    if signal is post_save and kwargs.get("created", False):
        sync_create_zio(instance)

    elif signal is post_delete:
        sync_delete_zio(instance)
