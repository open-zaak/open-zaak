from urllib.parse import urlparse

from django.utils.translation import ugettext_lazy as _

from django_loose_fk.drf import FKOrURLField, FKOrURLValidator
from rest_framework import serializers
from vng_api_common.oas import fetcher, obj_has_shape
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.documenten.models import EnkelvoudigInformatieObject

from ..loaders import AuthorizedRequestsLoader


class PublishValidator(FKOrURLValidator):
    publish_code = "not-published"
    publish_message = _("The resource is not published.")

    def set_context(self, serializer_field):
        # loose-fk field
        if isinstance(serializer_field, FKOrURLField):
            super().set_context(serializer_field)

    def __call__(self, value):
        # loose-fk field
        if value and isinstance(value, str):
            # not to double FKOrURLValidator
            try:
                super().__call__(value)
            except serializers.ValidationError:
                return
            value = self.resolver.resolve(self.host, value)

        if value.concept:
            raise serializers.ValidationError(
                self.publish_message, code=self.publish_code
            )


class LooseFkIsImmutableValidator(FKOrURLValidator):
    """
    Valideer dat de waarde van het FkOrUrlField niet wijzigt bij een update actie.
    """

    def __init__(self, *args, **kwargs):
        self.instance_path = kwargs.pop("instance_path", None)
        super().__init__(*args, **kwargs)

    def set_context(self, serializer_field):
        # loose-fk field
        if isinstance(serializer_field, FKOrURLField):
            super().set_context(serializer_field)

        # Determine the existing instance, if this is an update operation.
        self.serializer_field = serializer_field
        self.instance = getattr(serializer_field.parent, "instance", None)

    def __call__(self, new_value):
        # no instance -> it's not an update
        if not self.instance:
            return

        current_value = getattr(self.instance, self.serializer_field.field_name)

        # loose-fk field
        if new_value and isinstance(new_value, str):
            # not to double FKOrURLValidator
            try:
                super().__call__(new_value)
            except serializers.ValidationError:
                return

            new_value = self.resolver.resolve(self.host, new_value)

        if self.instance_path:
            for bit in self.instance_path.split("."):
                new_value = getattr(new_value, bit)

        if new_value != current_value:
            raise serializers.ValidationError(
                IsImmutableValidator.message, code=IsImmutableValidator.code
            )


class LooseFkResourceValidator(FKOrURLValidator):
    resource_message = _(
        "The URL {url} resource did not look like a(n) `{resource}`. Please provide a valid URL."
    )
    resource_code = "invalid-resource"

    def __init__(self, resource: str, oas_schema: str, *args, **kwargs):
        self.resource = resource
        self.oas_schema = oas_schema
        super().__init__(*args, **kwargs)

    def __call__(self, value: str):
        # not to double FKOrURLValidator
        try:
            super().__call__(value)
        except serializers.ValidationError:
            return

        # if local - do nothing
        parsed = urlparse(value)
        is_local = parsed.netloc == self.host
        if is_local:
            return

        obj = AuthorizedRequestsLoader.fetch_object(value, do_underscoreize=False)

        # check if the shape matches
        schema = fetcher.fetch(self.oas_schema)
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

        if not isinstance(informatieobject, EnkelvoudigInformatieObject):
            io_type = informatieobject.latest_version.informatieobjecttype
        else:
            io_type = informatieobject.informatieobjecttype

        # zaaktype/besluittype and informatieobjecttype should be both internal or external
        if bool(objecttype.pk) != bool(io_type.pk):
            raise serializers.ValidationError(message, code=code)

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
            related_iotypes = [
                iotype
                for iotype in objecttype_data.get("informatieobjecttypen", [])
                if iotype == iotype_url
            ]
            if not related_iotypes:
                raise serializers.ValidationError(message, code=code)
