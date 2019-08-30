import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.models import ObjectInformatieObject

logger = logging.getLogger(__name__)


def sync_create_bio(relation: BesluitInformatieObject):
    ObjectInformatieObject.objects.create(
        besluit=relation.besluit,
        informatieobject=relation.informatieobject,
        object_type="besluit",
    )


def sync_delete_bio(relation: BesluitInformatieObject):
    ObjectInformatieObject.objects.filter(
        besluit=relation.besluit,
        informatieobject=relation.informatieobject,
        object_type="besluit",
    ).delete()


@receiver([post_save, post_delete], sender=BesluitInformatieObject)
def sync_informatieobject_relation(
    sender, instance: BesluitInformatieObject = None, **kwargs
):
    signal = kwargs["signal"]
    if signal is post_save and kwargs.get("created", False):
        sync_create_bio(instance)

    elif signal is post_delete:
        sync_delete_bio(instance)
