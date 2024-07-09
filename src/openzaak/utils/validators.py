# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from rest_framework import serializers
from rest_framework.utils.representation import smart_repr
from rest_framework.validators import (
    UniqueTogetherValidator as _UniqueTogetherValidator,
)
from vng_api_common.oas import obj_has_shape
from vng_api_common.utils import get_resource_for_path, get_uuid_from_path
from vng_api_common.validators import IsImmutableValidator, URLValidator

from openzaak.api_standards import APIStandard
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.config.models import FeatureFlags

from ..loaders import AuthorizedRequestsLoader
from .serializer_fields import FKOrServiceUrlValidator

logger = logging.getLogger(__name__)


class PublishValidator(FKOrServiceUrlValidator):
    publish_code = "not-published"
    publish_message = _("The resource is not published.")

    def __call__(self, value, serializer_field):
        # check the feature flag to allow unpublished types. if that's enabled,
        # there's no point in checking anything beyond this as "everything goes"
        feature_flags = FeatureFlags.get_solo()
        if feature_flags.allow_unpublished_typen:
            return

        # loose-fk field
        if value and isinstance(value, str):
            # not to double FKOrURLValidator
            try:
                super().__call__(value, serializer_field)
            except serializers.ValidationError:
                return

            # the super class has added the resolved instance to the context
            context_key = self.get_context_cache_key(serializer_field)
            value = serializer_field.context[context_key]

        if value.concept:
            raise serializers.ValidationError(
                self.publish_message, code=self.publish_code
            )


class LooseFkIsImmutableValidator(FKOrServiceUrlValidator):
    """
    Valideer dat de waarde van het FkOrUrlField niet wijzigt bij een update actie.
    """

    def __init__(self, *args, **kwargs):
        self.instance_path = kwargs.pop("instance_path", None)
        super().__init__(*args, **kwargs)

    def __call__(self, new_value, serializer_field):
        instance = getattr(serializer_field.parent, "instance", None)

        # no instance -> it's not an update
        if not instance:
            return

        current_value = getattr(instance, serializer_field.field_name)

        # loose-fk field
        if new_value and isinstance(new_value, str):
            # not to double FKOrURLValidator
            try:
                super().__call__(new_value, serializer_field)
            except serializers.ValidationError:
                return

            # the super class has added the resolved instance to the context
            context_key = self.get_context_cache_key(serializer_field)
            new_value = serializer_field.context[context_key]

        if isinstance(current_value, EnkelvoudigInformatieObject) and isinstance(
            new_value, EnkelvoudigInformatieObject
        ):
            if settings.CMIS_ENABLED:
                new_value_url = new_value.get_url()
                current_value_url = current_value.get_url()
            else:
                new_value_url = new_value._initial_data["url"]
                current_value_url = current_value._initial_data["url"]

            if new_value_url != current_value_url:
                raise serializers.ValidationError(
                    IsImmutableValidator.message, code=IsImmutableValidator.code
                )
            return

        if self.instance_path:
            for bit in self.instance_path.split("."):
                new_value = getattr(new_value, bit)

        if new_value != current_value:
            raise serializers.ValidationError(
                IsImmutableValidator.message, code=IsImmutableValidator.code
            )


class ResourceValidatorMixin:
    def __init__(self, resource: str, api_standard: APIStandard, *args, **kwargs):
        self.resource = resource
        self.api_standard = api_standard
        super().__init__(*args, **kwargs)

    def _resolve_schema(self) -> dict:
        return self.api_standard.schema


class LooseFkResourceValidator(ResourceValidatorMixin, FKOrServiceUrlValidator):
    resource_message = _(
        "The URL {url} resource did not look like a(n) `{resource}`. Please provide a valid URL."
    )
    resource_code = "invalid-resource"

    def __call__(self, value: str, serializer_field):
        # not to double FKOrURLValidator
        try:
            super().__call__(value, serializer_field)
        except serializers.ValidationError:
            return

        # the super class has added the resolved instance to the context
        context_key = self.get_context_cache_key(serializer_field)
        resolved_instance = serializer_field.context[context_key]
        is_local = not isinstance(resolved_instance, ProxyMixin)
        # if local - do nothing
        if is_local:
            return

        # TODO: we can probably use the underlying data directly instead of doing
        # another lookup
        obj = AuthorizedRequestsLoader.fetch_object(value, do_underscoreize=False)

        # check if the shape matches
        schema = self._resolve_schema()
        if not obj_has_shape(obj, schema, self.resource):
            raise serializers.ValidationError(
                self.resource_message.format(url=value, resource=self.resource),
                code=self.resource_code,
            )

        return obj


class ObjecttypeInformatieobjecttypeRelationValidator:
    code = "missing-{}-informatieobjecttype-relation"
    message = _("Het informatieobjecttype hoort niet bij het {} van de {}.")

    def __init__(self, object_field: str = "zaak", objecttype_field: str = "zaaktype"):
        self.object_field = object_field
        self.objecttype_field = objecttype_field

    def __call__(self, attrs):
        code = self.code.format(self.objecttype_field)
        message = self.message.format(self.objecttype_field, self.object_field)

        informatieobject = attrs.get("informatieobject")
        object = attrs.get(self.object_field)
        if not informatieobject or not object:
            return

        objecttype = getattr(object, self.objecttype_field)

        if isinstance(informatieobject, ProxyMixin) and settings.CMIS_ENABLED:
            io_uuid = get_uuid_from_path(informatieobject._initial_data["url"])
            io = EnkelvoudigInformatieObject.objects.get(uuid=io_uuid)
            io_type = io.informatieobjecttype
        elif isinstance(informatieobject, EnkelvoudigInformatieObject):
            io_type = informatieobject.informatieobjecttype
        elif isinstance(informatieobject, str):
            io_path = urlparse(informatieobject).path
            io = get_resource_for_path(io_path)
            io_type = io.informatieobjecttype
        else:
            io_type = informatieobject.latest_version.informatieobjecttype

        # zaaktype/besluittype and informatieobjecttype should be both internal or external
        if bool(objecttype.pk) != bool(io_type.pk):
            msg_diff = _(
                "Het informatieobjecttype en het {objecttype_field} van de/het "
                "{object_field} moeten tot dezelfde catalogus behoren."
            ).format(
                objecttype_field=self.objecttype_field, object_field=self.object_field
            )
            raise serializers.ValidationError(msg_diff, code=code)

        # local zaaktype/besluittype
        if objecttype.pk:
            if not objecttype.informatieobjecttypen.filter(uuid=io_type.uuid).exists():
                raise serializers.ValidationError(message, code=code)

        # external zaaktype/besluittype - workaround since loose-fk field doesn't support m2m relations
        else:
            objecttype_url = objecttype._loose_fk_data["url"]
            iotype_url = io_type._loose_fk_data["url"]
            objecttype_data = AuthorizedRequestsLoader.fetch_object(
                objecttype_url, do_underscoreize=False
            )
            if iotype_url not in objecttype_data.get("informatieobjecttypen", []):
                raise serializers.ValidationError(message, code=code)


class UniqueTogetherValidator(_UniqueTogetherValidator):
    def __repr__(self):
        """
        The parent representation function iterates through the queryset and
        generates a representation for every object in the queryset. This is particularly
        problematic when CMIS is enabled and for each object a query to the DMS
        has to be done.
        """
        return "<{}(fields={})>".format(
            self.__class__.__name__, smart_repr(self.fields)
        )


class ResourceValidator(ResourceValidatorMixin, URLValidator):
    """
    Implement remote API resource validation.

    This is an alternative for :class:`vng_api_common.validators.ResourceValidator`
    leveraging local schema references before fetching them from public internet URLs.
    """

    def __call__(self, url: str):
        response = super().__call__(url)

        err_message = _(
            "The URL {url} resource did not look like a(n) `{resource}`. "
            "Please provide a valid URL."
        )
        error = serializers.ValidationError(
            err_message.format(url=url, resource=self.resource), code="invalid-resource"
        )

        # at this point, we know the URL actually exists
        try:
            obj = response.json()
        except json.JSONDecodeError:
            logger.info(
                "URL %s doesn't seem to point to a JSON endpoint", url, exc_info=True
            )
            raise error

        # obtain schema for shape matching
        schema = self._resolve_schema()

        # check if the shape matches
        if not obj_has_shape(obj, schema, self.resource):
            logger.info(
                "URL %s doesn't seem to point to a valid shape", url, exc_info=True
            )
            raise error

        return obj
