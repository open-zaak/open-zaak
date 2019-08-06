import logging

from django.core.cache import cache
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.utils.signals import sync_delete, sync_create
from openzaak.utils.urls import get_absolute_url

logger = logging.getLogger(__name__)


def sync_create_zio(relation: ZaakInformatieObject):
    # if informatieobject in local app
    if relation.informatieobject.pk:
        ObjectInformatieObject.objects.create(
            object=relation.zaak,
            informatieobject=relation.informatieobject,
            object_type='zaak'
        )

    zaak_url = get_absolute_url('zaak-detail', uuid=relation.zaak.uuid)

    logger.info("Zaak: %s", zaak_url)
    logger.info("Informatieobject: %s", relation.informatieobject)

    response = sync_create(
        relation.informatieobject,
        resource='objectinformatieobject',
        data={'object': zaak_url, 'informatieobject': relation.informatieobject, 'objectType': 'zaak'}
    )
    # save objectinformatieobject url for delete signal
    relation._objectinformatieobject = response['url']
    relation.save()


def sync_delete_zio(relation: ZaakInformatieObject):
    sync_delete(relation._objectinformatieobject, 'objectinformatieobject')


@receiver([post_save, pre_delete], sender=ZaakInformatieObject, dispatch_uid='sync.sync_informatieobject_relation')
def sync_informatieobject_relation(sender, instance: ZaakInformatieObject=None, **kwargs):
    signal = kwargs['signal']
    if signal is post_save and not instance._objectinformatieobject:
        sync_create_zio(instance)
    elif signal is pre_delete and instance._objectinformatieobject:
        # Add the uuid of the ZaakInformatieObject to the list of ZIOs that are
        # marked for delete, causing them not to show up when performing
        # GET requests on the ZRC, allowing the validation in the DRC to pass
        marked_zios = cache.get('zios_marked_for_delete', [])
        cache.set('zios_marked_for_delete', marked_zios + [instance.uuid])

        try:
            sync_delete_zio(instance)
        finally:
            marked_zios = cache.get('zios_marked_for_delete')
            marked_zios.remove(instance.uuid)
            cache.set('zios_marked_for_delete', marked_zios)
