# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from rest_framework import serializers
from vng_api_common.constants import ObjectTypes
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)
from zds_client import ClientError
from zgw_consumers.models import Service

from openzaak.utils import build_absolute_url

from ..models import ObjectInformatieObject
from ..validators import validate_status

logger = logging.getLogger(__name__)


class StatusValidator:
    """
    Wrap around openzaak.components.documenten.models.validate_status to output the errors to the
    correct field.
    """

    def set_context(self, serializer):
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs: dict):
        try:
            validate_status(
                status=attrs.get("status"),
                ontvangstdatum=attrs.get("ontvangstdatum"),
                instance=self.instance,
            )
        except ValidationError as exc:
            raise serializers.ValidationError(exc.error_dict)


class InformatieObjectUniqueValidator:
    """
    Validate that the relation between the object and informatieobject does not
    exist yet in the Documenten component
    """

    message = _("The fields object and informatieobject must make a unique set.")
    code = "unique"

    def __call__(self, context: OrderedDict):
        # The context contains the keys: informatieobject (eio), object_type (whether it is a relation with zaak or
        # besluit) and 'object' (the actual zaak or besluit). The 'object' key needs to be replaced with 'zaak'
        # or 'besluit' as there is no 'object' attribute in the objectinformatieobject model.
        zaak_or_besluit_object = context.pop("object")
        context.update({context["object_type"]: zaak_or_besluit_object})

        oios = ObjectInformatieObject.objects.filter(**context).exists()

        if oios:
            raise serializers.ValidationError(detail=self.message, code=self.code)


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van bronorganisatie en
    identificatie uniek is.
    """

    message = _("Deze identificatie bestaat al voor deze bronorganisatie")

    def __init__(self):
        super().__init__("bronorganisatie", "identificatie")


class RemoteRelationValidator:
    message = _(
        "The canonical remote relation still exists, this relation cannot be deleted."
    )
    code = "remote-relation-exists"

    def __init__(self, request=None):
        self.request = request

    def __call__(self, oio: ObjectInformatieObject):
        # external object
        if isinstance(oio.object, ProxyMixin):
            invalid = self._check_remote(oio)
        else:
            invalid = self._check_local(oio)

        if invalid:
            logger.info(
                "Relation between %s and informatieobject still exists", oio.object_type
            )
            raise serializers.ValidationError(self.message, self.code)

    @staticmethod
    def _check_local(oio: ObjectInformatieObject) -> bool:
        method_map = {
            ObjectTypes.zaak: "does_zaakinformatieobject_exist",
            ObjectTypes.besluit: "does_besluitinformatieobject_exist",
        }
        check_method = getattr(oio, method_map[oio.object_type])
        return check_method()

    def _check_remote(self, oio: ObjectInformatieObject) -> bool:
        object_url = oio.object._loose_fk_data["url"]

        if settings.CMIS_ENABLED:
            document_url = oio.get_informatieobject_url()
        else:
            default_version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]
            document_url = build_absolute_url(
                oio.informatieobject.latest_version.get_absolute_api_url(
                    version=default_version
                ),
                request=self.request,
            )

        # obtain a client for the remote API. this should exist, otherwise loose-fk
        # would not have been able to load this resource :-)
        client = Service.get_client(object_url)
        assert client is not None, f"Could not retrieve client for object {object_url}"

        try:
            zios = client.list(
                f"{oio.object_type}informatieobject",
                query_params={
                    "informatieobject": document_url,
                    oio.object_type: object_url,
                },
            )
        except ClientError as exc:
            raise serializers.ValidationError(
                exc.args[0], code="relation-lookup-error"
            ) from exc

        # if there are ZIOS returned, this means the source relation was not destroyed
        # yet
        return len(zios) > 0


class CreateRemoteRelationValidator:
    message = _(
        "The canonical remote relation does not exist, this relation cannot be created."
    )
    code = "inconsistent-relation"

    def __init__(self, request=None):
        self.request = request

    def __call__(self, document, object, object_type):
        object_url = object._loose_fk_data["url"]

        if settings.CMIS_ENABLED:
            document_url = document
        else:
            default_version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]
            document_url = build_absolute_url(
                document.latest_version.get_absolute_api_url(version=default_version),
                request=self.request,
            )

        # obtain a client for the remote API. this should exist, otherwise loose-fk
        # would not have been able to load this resource :-)
        client = Service.get_client(object_url)
        assert client is not None, f"Could not retrieve client for object {object_url}"

        try:
            remote_relations = client.list(
                f"{object_type}informatieobject",
                query_params={
                    "informatieobject": document_url,
                    object_type: object_url,
                },
            )
        except ClientError as exc:
            raise serializers.ValidationError(
                exc.args[0], code="relation-lookup-error"
            ) from exc

        if not len(remote_relations):
            raise serializers.ValidationError(self.message, self.code)
