import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from openzaak.components.besluiten.models import (
    Besluit, BesluitInformatieObject
)
from openzaak.components.zaken.models import ZaakBesluit
from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.utils.urls import get_absolute_url
from openzaak.utils.signals import sync_create, sync_delete


logger = logging.getLogger(__name__)


def sync_create_bio(relation: BesluitInformatieObject):
    # if informatieobject in local app
    if relation.informatieobject.pk:
        ObjectInformatieObject.objects.create(
            object=relation.besluit,
            informatieobject=relation.informatieobject,
            object_type='besluit'
        )

    besluit_url = get_absolute_url('besluit-detail', uuid=relation.besluit.uuid)

    logger.info("Besluit: %s", besluit_url)
    logger.info("Informatieobject: %s", relation.informatieobject)

    response = sync_create(
        relation.informatieobject,
        resource='objectinformatieobject',
        data={'object': besluit_url, 'informatieobject': relation.informatieobject, 'objectType': 'besluit'}
    )
    # save objectinformatieobject url for delete signal
    relation._objectinformatieobject = response['url']
    relation.save()


def sync_create_besluit(besluit: Besluit):
    # if zaak is in local app
    if besluit.zaak.pk:
        ZaakBesluit.objects.create(besluit=besluit, zaak=besluit.zaak)

    besluit_url = get_absolute_url('besluit-detail', uuid=besluit.uuid)

    logger.info("Zaak object: %s", besluit.zaak)
    logger.info("Besluit object: %s", besluit_url)

    response = sync_create(
        besluit.zaak,
        resource='zaakbesluit',
        data={'besluit': besluit_url},
        pattern_url=f"{besluit.zaak}/irrelevant"
    )
    # save ZaakBesluit url for delete signal
    besluit._zaakbesluit = response['url']
    besluit.save()


def sync_delete_besluit(besluit: Besluit):
    sync_delete(besluit._zaakbesluit, 'zaakbesluit')


def sync_delete_bio(relation: BesluitInformatieObject):
    sync_delete(relation._objectinformatieobject, 'objectinformatieobject')


@receiver([post_save, pre_delete], sender=BesluitInformatieObject)
def sync_informatieobject_relation(sender, instance: BesluitInformatieObject=None, **kwargs):
    signal = kwargs['signal']
    if signal is post_save and not instance._objectinformatieobject:
        sync_create_bio(instance)

    elif signal is pre_delete and instance._objectinformatieobject:
        # Add the uuid of the BesluitInformatieObject to the list of bios that are
        # marked for delete, causing them not to show up when performing
        # GET requests on the BRC, allowing the validation in the DRC to pass
        marked_bios = cache.get('bios_marked_for_delete', [])
        cache.set('bios_marked_for_delete', marked_bios + [instance.uuid])
        try:
            sync_delete_bio(instance)
        finally:
            marked_bios = cache.get('bios_marked_for_delete')
            marked_bios.remove(instance.uuid)
            cache.set('bios_marked_for_delete', marked_bios)


@receiver([post_save, post_delete], sender=Besluit)
def sync_besluit(sender, instance: Besluit = None, **kwargs):
    signal = kwargs['signal']

    if signal is post_save and instance.zaak and not instance._zaakbesluit:
        sync_create_besluit(instance)

    elif signal is post_delete and instance._zaakbesluit:  # remote, local will be deleted automatically
        sync_delete_besluit(instance)
