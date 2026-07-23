# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from typing import Type

from django.db import models, transaction

from vng_api_common.audittrails.audits import Audit
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.audittrails.viewsets import (
    AuditTrailMixin,
)
from vng_api_common.constants import CommonResourceAction
from vng_api_common.utils import get_uuid_from_path


class MultipleAuditTrailsMixin(AuditTrailMixin):
    audits: list[Audit]
    audittrail_main_resource_keys: dict[str, str]

    _AUDIT_NAMESPACE_MAPPING = {"BRC": "besluiten", "ZRC": "zaken"}

    def _replace_namespace(self, url: str, namespace: str) -> str:
        # TODO move to deprecated api utils
        prefix, sep, rest = url.partition("/api")
        if not sep:
            return url

        base, _, old_namespace = prefix.rpartition("/")
        return f"{base}/{namespace}{sep}{rest}"

    def _replace_namespaces(
        self, data: dict, fields: list[str], namespace: str
    ) -> list[str]:
        new_data = data.copy()
        for field in fields:
            new_data[field] = self._replace_namespace(new_data[field], namespace)

        return new_data

    def _get_nested_main_resource_url_from_instance(
        self, key: str, instance: Type[models.Model]
    ) -> str | None:
        """Returns the url of an nested FK field"""
        obj = instance
        for field in key.split("."):
            obj = getattr(obj, field, None)
        return obj.get_absolute_api_url(request=self.request) if obj else None

    def _get_audittrail_main_object_url(
        self, data: dict, audit: Audit, instance: Type[models.Model]
    ) -> str | None:
        if self.basename == audit.main_resource:
            return data["url"]

        if audit.main_resource not in data:
            # TODO WATCH OUT MultipleChannelNotificationMixin methods are also accessible since everything is a mixin on the viewset
            url = self._get_nested_main_resource_url_from_instance(
                self.audittrail_main_resource_keys[audit.component_name],
                instance,
            )
        else:
            url = data[audit.main_resource]
            if url == "":
                url = None

        return url

    def _handle_namespacing(
        self,
        audit: Audit,
        instance: Type[models.Model],
        version_before_edit: dict | None = None,
        version_after_edit: dict | None = None,
    ):
        fields = getattr(self, "audittrail_replace_urls_for", [])
        fields.append("url")

        if version_before_edit:
            version_before_edit = self._replace_namespaces(
                version_before_edit,
                fields,
                self._AUDIT_NAMESPACE_MAPPING[audit.component_name],
            )

        if version_after_edit:
            version_after_edit = self._replace_namespaces(
                version_after_edit,
                fields,
                self._AUDIT_NAMESPACE_MAPPING[audit.component_name],
            )

        data = version_after_edit or version_before_edit
        main_object = self._get_audittrail_main_object_url(data, audit, instance)

        return main_object, version_before_edit, version_after_edit


class MultipleAuditTrailsCreateMixin(MultipleAuditTrailsMixin):
    # TODO
    def get_audittrail_instance(self, response):
        if self._audittrail_serializer is not None:
            return self._audittrail_serializer.instance
        zaak_uuid = get_uuid_from_path(response.data["url"])
        instance = self.get_queryset().get(uuid=zaak_uuid)  # type: ignore
        return instance

    # TODO
    def perform_create(self, serializer):
        super().perform_create(serializer)  # type: ignore
        # cache for future re-use
        self._audittrail_serializer = serializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)  # type: ignore
        instance = self.get_audittrail_instance(response)
        version_after_edit = response.data

        for audit in self.audits:
            main_object, _, version_after_edit = self._handle_namespacing(
                audit, instance, version_after_edit=version_after_edit
            )

            # Do not create audittrail if audit main resource does not exist on the instance
            # E.g. besluit zaak is not required
            if main_object is None:
                continue

            self.create_audittrail(
                response.status_code,
                CommonResourceAction.create,
                version_before_edit=None,
                version_after_edit=version_after_edit,
                unique_representation=instance.unique_representation(),
                audit=audit,
                main_object=main_object,
            )
        return response


class MultipleAuditTrailsUpdateMixin(MultipleAuditTrailsMixin):
    def update(self, request, *args, **kwargs):
        # Retrieve the data stored in the object before updating
        instance = self.get_object()  # type: ignore
        serializer = self.get_serializer(instance)  # type: ignore
        version_before_edit = serializer.data

        action = (
            CommonResourceAction.partial_update
            if kwargs.get("partial", False)
            else CommonResourceAction.update
        )

        response = super().update(request, *args, **kwargs)  # type: ignore
        version_after_edit = response.data

        for audit in self.audits:
            main_object, version_before_edit, version_after_edit = (
                self._handle_namespacing(
                    audit,
                    instance,
                    version_before_edit=version_before_edit,
                    version_after_edit=version_after_edit,
                )
            )

            # Do not create audittrail if audit main resource does not exist on the instance
            # E.g. besluit zaak is not required
            if main_object is None:
                continue

            self.create_audittrail(
                response.status_code,
                action,
                version_before_edit=version_before_edit,
                version_after_edit=version_after_edit,
                unique_representation=instance.unique_representation(),
                audit=audit,
                main_object=main_object,
            )
        return response


class MultipleAuditTrailsDestroyMixin(MultipleAuditTrailsMixin):
    def destroy(self, request, *args, **kwargs):
        # Retrieve the data stored in the object before updating
        instance = self.get_object()  # type: ignore
        serializer = self.get_serializer(instance)  # type: ignore
        version_before_edit = serializer.data

        with transaction.atomic():
            response = super().destroy(request, *args, **kwargs)
            for audit in self.audits:
                main_object, version_before_edit, _ = self._handle_namespacing(
                    audit, instance, version_before_edit=version_before_edit
                )

                # Do not create audittrail if audit main resource does not exist on the instance
                # E.g. besluit zaak is not required
                if main_object is None:
                    continue

                # If the resource being deleted is the main resource, delete all the
                # audittrails associated with it
                if self.basename == audit.main_resource:  # type: ignore
                    self._destroy_related_audittrails(version_before_edit["url"])
                else:
                    self.create_audittrail(
                        response.status_code,
                        CommonResourceAction.destroy,
                        version_before_edit=version_before_edit,
                        version_after_edit=None,
                        unique_representation=instance.unique_representation(),
                        audit=audit,
                        main_object=main_object,
                    )

            return response

    def _destroy_related_audittrails(self, main_object_url):
        AuditTrail.objects.filter(hoofd_object=main_object_url).delete()


class MultipleAuditTrailsViewsetMixin(
    MultipleAuditTrailsCreateMixin,
    MultipleAuditTrailsUpdateMixin,
    MultipleAuditTrailsDestroyMixin,
):
    pass
