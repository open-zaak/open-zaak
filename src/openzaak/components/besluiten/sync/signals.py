import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.urls import reverse

from vng_api_common.models import APICredential
from zds_client import Client, extract_params, get_operation_url

from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject

logger = logging.getLogger(__name__)


class SyncError(Exception):
    pass


def sync_create_bio(relation: BesluitInformatieObject):
    operation = 'create'

    # build the URL of the Besluit
    path = reverse('besluit-detail', kwargs={
        'version': settings.REST_FRAMEWORK['DEFAULT_VERSION'],
        'uuid': relation.besluit.uuid,
    })
    domain = Site.objects.get_current().domain
    protocol = 'https' if settings.IS_HTTPS else 'http'
    besluit_url = f'{protocol}://{domain}{path}'

    logger.info("Besluit: %s", besluit_url)
    logger.info("Informatieobject: %s", relation.informatieobject)

    # Define the remote resource with which we need to interact
    resource = 'objectinformatieobject'
    client = Client.from_url(relation.informatieobject)

    # TODO?
    client.auth = APICredential.get_auth(relation.informatieobject)

    try:
        operation_function = getattr(client, operation)
        operation_function(
            resource,
            {'object': besluit_url, 'informatieobject': relation.informatieobject, 'objectType': 'besluit'}
        )
    except Exception as exc:
        logger.error(f"Could not {operation} remote relation", exc_info=1)
        raise SyncError(f"Could not {operation} remote relation") from exc


def sync_delete_bio(relation: BesluitInformatieObject):
    operation = 'delete'

    # build the URL of the Besluit
    path = reverse('besluit-detail', kwargs={
        'version': settings.REST_FRAMEWORK['DEFAULT_VERSION'],
        'uuid': relation.besluit.uuid,
    })
    domain = Site.objects.get_current().domain
    protocol = 'https' if settings.IS_HTTPS else 'http'
    besluit_url = f'{protocol}://{domain}{path}'

    logger.info("Besluit: %s", besluit_url)
    logger.info("Informatieobject: %s", relation.informatieobject)

    # Define the remote resource with which we need to interact
    resource = 'objectinformatieobject'
    client = Client.from_url(relation.informatieobject)
    client.auth = APICredential.get_auth(relation.informatieobject)

    # Retrieve the url of the relation between the object and the
    response = client.list(resource, query_params={'object': besluit_url})
    try:
        relation_url = response[0]['url']
    except IndexError as exc:
        msg = "No relations found in DRC for this Besluit"
        logger.error(msg, exc_info=1)
        raise IndexError(msg) from exc

    try:
        operation_function = getattr(client, operation)
        operation_function(resource, url=relation_url)
    except Exception as exc:
        logger.error(f"Could not {operation} remote relation", exc_info=1)
        raise SyncError(f"Could not {operation} remote relation") from exc


def sync_create_besluit(besluit: Besluit):

    # build the URL of the besluit
    path = reverse('besluit-detail', kwargs={
        'version': settings.REST_FRAMEWORK['DEFAULT_VERSION'],
        'uuid': besluit.uuid,
    })
    domain = Site.objects.get_current().domain
    protocol = 'https' if settings.IS_HTTPS else 'http'
    besluit_url = f'{protocol}://{domain}{path}'

    logger.info("Zaak object: %s", besluit.zaak)
    logger.info("Besluit object: %s", besluit_url)

    # figure out which remote resource we need to interact with
    client = Client.from_url(besluit.zaak)
    client.auth = APICredential.get_auth(besluit.zaak)

    try:
        pattern = get_operation_url(client.schema, f'zaakbesluit_create', pattern_only=True)
    except ValueError as exc:
        raise SyncError("Could not determine remote operation") from exc

    # The real resource URL is extracted from the ``openapi.yaml`` based on
    # the operation
    params = extract_params(f"{besluit.zaak}/irrelevant", pattern)

    try:
        response = client.create('zaakbesluit', {'besluit': besluit_url}, **params)
    except Exception as exc:
        logger.error(f"Could not create zaakbesluit", exc_info=1)
        raise SyncError(f"Could not create zaakbesluit") from exc

    # save ZaakBesluit url for delete signal
    besluit._zaakbesluit = response['url']
    besluit.save()


def sync_delete_besluit(besluit: Besluit):
    client = Client.from_url(besluit._zaakbesluit)
    client.auth = APICredential.get_auth(besluit._zaakbesluit)
    try:
        client.delete('zaakbesluit', url=besluit._zaakbesluit)
    except Exception as exc:
        logger.error(f"Could not delete ZaakBesluit", exc_info=1)
        raise SyncError(f"Could not delete ZaakBesluit") from exc


@receiver([post_save, pre_delete], sender=BesluitInformatieObject, dispatch_uid='sync.sync_informatieobject_relation')
def sync_informatieobject_relation(sender, instance: BesluitInformatieObject=None, **kwargs):
    signal = kwargs['signal']
    if signal is post_save and kwargs.get('created', False):
        sync_create_bio(instance)
    elif signal is pre_delete:
        # Add the uuid of the BesluitInformatieObject to the list of bios that are
        # marked for delete, causing them not to show up when performing
        # GET requests on the BRC, allowing the validation in the DRC to pass
        marked_bios = cache.get('bios_marked_for_delete')
        if marked_bios:
            cache.set('bios_marked_for_delete', marked_bios + [instance.uuid])
        else:
            cache.set('bios_marked_for_delete', [instance.uuid])

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
    elif signal is post_delete and instance._zaakbesluit:
        sync_delete_besluit(instance)
