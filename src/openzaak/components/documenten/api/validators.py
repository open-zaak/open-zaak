# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
from collections import OrderedDict
from typing import Union

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from requests import RequestException
from rest_framework import serializers
from vng_api_common.client import ClientError, get_client, to_internal_data
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)

from openzaak.utils import build_absolute_url
from openzaak.utils.serializers import get_from_serializer_data_or_instance

from ..constants import ObjectInformatieObjectTypes
from ..models import ObjectInformatieObject
from ..validators import validate_status

logger = logging.getLogger(__name__)


class StatusValidator:
    """
    Wrap around openzaak.components.documenten.models.validate_status to output the errors to the
    correct field.
    """

    requires_context = True

    def __call__(self, attrs: dict, serializer):
        instance = getattr(serializer, "instance", None)
        try:
            validate_status(
                status=attrs.get("status"),
                ontvangstdatum=attrs.get("ontvangstdatum"),
                instance=instance,
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

    def __call__(self, attrs: OrderedDict):
        # The attrs contain the keys:
        # * 'informatieobject' (eio)
        # * 'object_type' (whether it is a relation with zaak, besluit or verzoek)
        # * 'object' (the actual zaak, besluit or verzoek)
        #
        # The 'object' key needs to be replaced with 'zaak', 'besluit' or 'verzoek' as
        # there is no 'object' attribute in the objectinformatieobject model.
        object = attrs.pop("object")
        attrs.update({attrs["object_type"]: object})

        oios = ObjectInformatieObject.objects.filter(**attrs).exists()

        if oios:
            raise serializers.ValidationError(detail=self.message, code=self.code)


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van bronorganisatie en
    identificatie uniek is.
    """

    message = _(
        "Deze identificatie ({identificatie}) bestaat al voor deze bronorganisatie"
    )

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
        if isinstance(oio.object, ProxyMixin) or isinstance(oio.object, str):
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
            ObjectInformatieObjectTypes.zaak: "does_zaakinformatieobject_exist",
            ObjectInformatieObjectTypes.besluit: "does_besluitinformatieobject_exist",
        }
        check_method = getattr(oio, method_map[oio.object_type])
        return check_method()

    def _check_remote(self, oio: ObjectInformatieObject) -> bool:
        if isinstance(oio.object, str):
            object_url = oio.object
        else:
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
        client = get_client(object_url, raise_exceptions=True)

        try:
            zios: list = to_internal_data(
                client.get(
                    f"{oio.object_type}informatieobjecten",
                    params={
                        "informatieobject": document_url,
                        oio.object_type: object_url,
                    },
                )
            )
        except (RequestException, ClientError) as exc:
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
        object_url = object if isinstance(object, str) else object._loose_fk_data["url"]

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
        client = get_client(object_url, raise_exceptions=True)
        assert client

        try:
            remote_relations: list = to_internal_data(
                client.get(
                    f"{object_type}informatieobjecten",
                    params={
                        "informatieobject": document_url,
                        object_type: object_url,
                    },
                )
            )
        except (RequestException, ClientError) as exc:
            raise serializers.ValidationError(
                exc.args[0], code="relation-lookup-error"
            ) from exc

        if not len(remote_relations):
            raise serializers.ValidationError(self.message, self.code)


def is_not_empty(value: Union[str, int, bool, dict]) -> bool:
    if isinstance(value, dict):
        return any(value.values())

    return bool(value)


class VerzendingAddressValidator:
    """
    Check that Verzending can have only one attribute filled of the following:
    * binnenlands_correspondentieadres
    * buitenlands_correspondentieadres
    * correspondentie_postadres
    * telefoonnummer
    * emailadres
    * mijn_overheid
    * faxnummer

    This logic is not described in DRC OAS, and this validator is based
    on the DRC reference implementation

    The question about this logic and its absence in the OAS -
    https://github.com/VNG-Realisatie/gemma-zaken/issues/2297
    """

    requires_context = True
    message = _("Verzending must contain precisely one correspondentieadress")
    code = "invalid-address"

    def __call__(self, attrs: dict, serializer: serializers.Serializer):
        # for POST and PUT we just check that the contact channel attribute is the only one
        if not serializer.partial:
            non_empty_count = (
                is_not_empty(attrs.get("binnenlands_correspondentieadres"))
                + is_not_empty(attrs.get("buitenlands_correspondentieadres"))
                + is_not_empty(attrs.get("correspondentie_postadres"))
                + is_not_empty(attrs.get("telefoonnummer"))
                + is_not_empty(attrs.get("emailadres"))
                + is_not_empty(attrs.get("mijn_overheid"))
                + is_not_empty(attrs.get("telefoonnummer"))
            )

            if non_empty_count != 1:
                raise serializers.ValidationError(detail=self.message, code=self.code)

        else:
            # for PATCH we check that if the instance has one contact attribute filled
            # another contact attribute can't be patched
            non_empty_partial_count = (
                is_not_empty(
                    get_from_serializer_data_or_instance(
                        "binnenlands_correspondentieadres", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "buitenlands_correspondentieadres", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "correspondentie_postadres", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "telefoonnummer", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "emailadres", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "mijn_overheid", attrs, serializer
                    )
                )
                + is_not_empty(
                    get_from_serializer_data_or_instance(
                        "telefoonnummer", attrs, serializer
                    )
                )
            )
            if non_empty_partial_count != 1:
                raise serializers.ValidationError(detail=self.message, code=self.code)
