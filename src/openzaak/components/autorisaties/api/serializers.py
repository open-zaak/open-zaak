# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_loose_fk.loaders import BaseLoader
from django_loose_fk.utils import get_resource_for_path
from furl import furl
from rest_framework.exceptions import ValidationError
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.authorizations.serializers import (
    ApplicatieSerializer as _ApplicatieSerializer,
    AutorisatieBaseSerializer,
)
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import JWTSecret

from openzaak.utils import build_absolute_url

logger = logging.getLogger(__name__)


class ApplicatieSerializer(_ApplicatieSerializer):
    def to_representation(self, instance):
        """
        Join the regular `Applicatie.autorisaties` with `CatalogusAutorisaties`, by
        adding a virtual `Autorisatie` for each zaak/besluit/informatieobjecttype in the
        linked `Catalogus`
        """
        from ..forms import COMPONENT_TO_FIELDS_MAP

        data = super().to_representation(instance)

        virtual_autorisaties = []
        for catalogus_autorisatie in instance.catalogusautorisatie_set.all():
            # Get the related zaak/informatieobject/besluittypen related to this Catalogus
            # (dependent on the component of the CatalogusAutorisatie in the current iteration)
            type_field = COMPONENT_TO_FIELDS_MAP[catalogus_autorisatie.component][
                "_autorisatie_type_field"
            ]

            # Instead of accessing the *type_set using `getattr`, we explicitly use the
            # dot notation here, because the `getattr` approach means we cannot rely on the
            # optimization `prefetch_related` brings to the queryset defined on the viewset
            if catalogus_autorisatie.component == ComponentTypes.zrc:
                types = catalogus_autorisatie.catalogus.zaaktype_set.all()
            elif catalogus_autorisatie.component == ComponentTypes.drc:
                types = catalogus_autorisatie.catalogus.informatieobjecttype_set.all()
            elif catalogus_autorisatie.component == ComponentTypes.brc:
                types = catalogus_autorisatie.catalogus.besluittype_set.all()

            virtual_autorisaties += [
                Autorisatie(
                    **{
                        "applicatie": instance,
                        "component": catalogus_autorisatie.component,
                        "scopes": catalogus_autorisatie.scopes,
                        "max_vertrouwelijkheidaanduiding": catalogus_autorisatie.max_vertrouwelijkheidaanduiding,
                        type_field: build_absolute_url(
                            reverse(
                                f"{type_field}-detail",
                                kwargs={
                                    "uuid": str(type.uuid),
                                    "version": settings.REST_FRAMEWORK[
                                        "DEFAULT_VERSION"
                                    ],
                                },
                            ),
                            request=self.context["request"],
                        ),
                    }
                )
                for type in types
            ]

        serializer = AutorisatieBaseSerializer(virtual_autorisaties, many=True)
        data["autorisaties"] = data["autorisaties"] + serializer.data
        return data

    def create_missing_credentials(self, applicatie: Applicatie):
        # create missing jwtsecret objects for admin page
        current_credentials = list(
            JWTSecret.objects.filter(identifier__in=applicatie.client_ids).values_list(
                "identifier", flat=True
            )
        )
        new_credentials = []
        for client_id in applicatie.client_ids:
            if client_id not in current_credentials:
                new_credentials.append(JWTSecret(identifier=client_id, secret=""))

        JWTSecret.objects.bulk_create(new_credentials)

    @transaction.atomic
    def create(self, validated_data):
        applicatie = super().create(validated_data)
        self.create_missing_credentials(applicatie)

        return applicatie

    @transaction.atomic
    def update(self, instance, validated_data):
        # Because CatalogusAutorisaties cannot be managed via the API, we delete them
        # to avoid conflicts between regular Autorisaties and CatalogusAutorisaties
        if (
            "autorisaties" in validated_data
            and instance.catalogusautorisatie_set.exists()
        ):
            logger.info(
                "Updating Applicatie %s via the API, deleting existing CatalogusAutorisaties"
            )
            instance.catalogusautorisatie_set.all().delete()

        applicatie = super().update(instance, validated_data)
        self.create_missing_credentials(applicatie)

        return applicatie

    def validate(self, attrs):
        # Check overlap between autorisaties *typen and CatalogusAutorisaties
        if self.instance and self.instance.catalogusautorisatie_set.exists():
            from ..forms import COMPONENT_TO_FIELDS_MAP

            catalogus_autorisatie_mapping = {
                catalogus_autorisatie.catalogus: catalogus_autorisatie
                for catalogus_autorisatie in self.instance.catalogusautorisatie_set.all()
            }
            loader = BaseLoader()
            for autorisatie in attrs.get("autorisaties", []):
                type_field = COMPONENT_TO_FIELDS_MAP.get(
                    autorisatie["component"], {}
                ).get("_autorisatie_type_field")

                if type_field and loader.is_local_url(autorisatie[type_field]):
                    path = str(furl(autorisatie[type_field]).path)
                    instance = loader.load_local_object(
                        path, get_resource_for_path(path)
                    )
                    if matching_autorisatie := catalogus_autorisatie_mapping.get(
                        instance.catalogus
                    ):
                        if set(matching_autorisatie.scopes).intersection(
                            set(autorisatie["scopes"])
                        ):
                            raise ValidationError(
                                _(
                                    "Cannot create Autorisatie for component {component} and type {type}, there is "
                                    "a CatalogusAutorisatie with overlapping scopes"
                                ).format(
                                    component=autorisatie["component"],
                                    type=autorisatie[type_field],
                                ),
                                code="catalogus-autorisatie-exists",
                            )
        return super().validate(attrs)
