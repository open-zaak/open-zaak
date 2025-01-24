# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Optional

from django.db import models

from rest_framework import serializers
from rest_framework.response import Response

from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
from openzaak.components.zaken.models import Zaak

from .exceptions import ZaakClosed
from .serializers import ZaakSerializer


class ClosedZaakMixin:
    def _has_override(self, zaak: Zaak) -> bool:
        jwt_auth = self.request.jwt_auth
        zaak_data = ZaakSerializer(zaak, context={"request": self.request}).data
        return jwt_auth.has_auth(
            scopes=SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
            zaaktype=zaak_data["zaaktype"],
            vertrouwelijkheidaanduiding=zaak_data["vertrouwelijkheidaanduiding"],
            init_component=self.queryset.model._meta.app_label,
        )

    def _check_zaak_closed(self, zaak: Optional[Zaak] = None) -> None:
        """
        Raise ZaakClosed if an attempt is made to modify a closed zaak.

        Unless you have the scope SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN, an application
        is not allowed to mutate a closed zaak.
        """
        # if there is no zaak involved, nothing to do
        if not zaak:
            return

        # zaak open -> don't raise exceptions
        if not zaak.is_closed:
            return

        # zaak is closed - do we have the special i-can-do-anything permission?
        if self._has_override(zaak):
            return

        raise ZaakClosed()

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        """
        Block the create if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        zaak = serializer.validated_data.get("zaak")
        self._check_zaak_closed(zaak)
        super().perform_create(serializer)

    def perform_update(self, serializer: serializers.ModelSerializer) -> None:
        """
        Block the update if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        zaak = serializer.instance.zaak
        self._check_zaak_closed(zaak)
        super().perform_update(serializer)

    def perform_destroy(self, instance: models.Model) -> None:
        """
        Block the destroy if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        zaak = instance.zaak
        self._check_zaak_closed(zaak)
        super().perform_destroy(instance)


class UpdateOnlyModelMixin:
    """
    Update mixin, which supports PUT but doesn't support PATCH
    Copied from DRF
    """

    def update(self, request, *args, **kwargs):
        kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()
