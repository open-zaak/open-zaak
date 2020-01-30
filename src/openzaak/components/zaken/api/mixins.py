from django.db import models

from rest_framework import serializers

from .exceptions import ZaakClosed


class ClosedZaakMixin:
    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        """
        Block the create if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        zaak = serializer.validated_data.get("zaak")
        if zaak and zaak.is_closed:
            raise ZaakClosed()

        super().perform_create(serializer)

    def perform_update(self, serializer: serializers.ModelSerializer) -> None:
        """
        Block the update if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        zaak = serializer.instance.zaak
        if zaak and zaak.is_closed:
            raise ZaakClosed()

        super().perform_update(serializer)

    def perform_destroy(self, instance: models.Model) -> None:
        """
        Block the destroy if the related zaak is closed.

        :raises: PermissionDenied if the related Zaak is closed.
        """
        if instance.zaak and instance.zaak.is_closed:
            raise ZaakClosed()

        super().perform_destroy(instance)
