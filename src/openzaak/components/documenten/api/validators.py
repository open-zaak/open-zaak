from collections import OrderedDict

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from openzaak.components.documenten.models import ObjectInformatieObject
from openzaak.components.documenten.models.validators import validate_status
from rest_framework import serializers
from vng_api_common.models import APICredential
from vng_api_common.tests.urls import reverse
from zds_client import ClientError

from openzaak.utils.urls import get_absolute_url


class StatusValidator:
    """
    Wrap around openzaak.components.documenten.models.validate_status to output the errors to the
    correct field.
    """

    def set_context(self, serializer):
        self.instance = getattr(serializer, 'instance', None)

    def __call__(self, attrs: dict):
        try:
            validate_status(
                status=attrs.get('status'),
                ontvangstdatum=attrs.get('ontvangstdatum'),
                instance=self.instance
            )
        except ValidationError as exc:
            raise serializers.ValidationError(exc.error_dict)


class ObjectInformatieObjectValidator:
    """
    Validate that the INFORMATIEOBJECT is already linked to the OBJECT in the remote component.
    """
    message = _('Het informatieobject is in het {component} nog niet gerelateerd aan het object.')
    code = 'inconsistent-relation'

    def __call__(self, context: OrderedDict):
        object_url = context['object']
        informatieobject_uuid = str(context['informatieobject'].latest_version.uuid)
        object_type = context['object_type']

        informatieobject_url = get_absolute_url(
            'enkelvoudiginformatieobject-detail',
            uuid=informatieobject_uuid
        )

        # dynamic so that it can be mocked in tests easily
        Client = import_string(settings.ZDS_CLIENT_CLASS)
        client = Client.from_url(object_url)
        client.auth = APICredential.get_auth(object_url)
        try:
            if object_type == 'zaak':
                resource = 'zaakinformatieobject'
                component = 'ZRC'
            elif object_type == 'besluit':
                resource = 'besluitinformatieobject'
                component = 'BRC'
            oios = client.list(resource, query_params={
                object_type: object_url,
                'informatieobject': informatieobject_url
            })

        except ClientError as exc:
            raise serializers.ValidationError(
                exc.args[0],
                code='relation-validation-error'
            ) from exc

        if len(oios) == 0:
            raise serializers.ValidationError(
                self.message.format(component=component),
                code=self.code
            )


class RemoteRelationValidator:
    message = _("The canonical remote relation still exists, this relation cannot be deleted.")
    code = "remote-relation-exists"

    def __call__(self, object_informatie_object: ObjectInformatieObject):
        object_url = object_informatie_object.object

        informatieobject_url = get_absolute_url(
            'enkelvoudiginformatieobject-detail',
            uuid=object_informatie_object.informatieobject.latest_version.uuid
        )

        Client = import_string(settings.ZDS_CLIENT_CLASS)
        client = Client.from_url(object_url)
        client.auth = APICredential.get_auth(object_url)

        resource = f"{object_informatie_object.object_type}informatieobject"

        try:
            relations = client.list(resource, query_params={
                object_informatie_object.object_type: object_url,
                'informatieobject': informatieobject_url,
            })
        except ClientError as exc:
            raise serializers.ValidationError(
                exc.args[0],
                code='relation-lookup-error'
            ) from exc

        if len(relations) >= 1:
            raise serializers.ValidationError(self.message, code=self.code)


class InformatieObjectUniqueValidator:
    """
    Validate that the relation between the object and informatieobject does not
    exist yet in the DRC
    """
    message = _('The fields {field_names} must make a unique set.')
    code = 'unique'

    def __init__(self, remote_resource_field, field: str):
        self.remote_resource_field = remote_resource_field
        self.field = field

    def __call__(self, context: OrderedDict):
        object_url = context['object']
        informatieobject = context['informatieobject']

        oios = informatieobject.objectinformatieobject_set.filter(object=object_url)

        if oios:
            field_names = (self.remote_resource_field, self.field)
            raise serializers.ValidationError(
                detail=self.message.format(field_names=field_names),
                code=self.code
            )
