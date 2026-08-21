# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import structlog
from rest_framework import serializers
from vng_api_common.authorizations.validators import (
    AutorisatieValidator,
)
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import JWTSecret
from vng_api_common.polymorphism import Discriminator, PolymorphicSerializer
from vng_api_common.serializers import add_choice_values_help_text

from openzaak.components.autorisaties.api.validators import UniqueClientIDValidator
from openzaak.components.autorisaties.models import Applicatie, Autorisatie

logger = structlog.stdlib.get_logger(__name__)


class ZaakTypeAutorisatieSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Autorisatie
        fields = ("zaaktype", "max_vertrouwelijkheidaanduiding")
        extra_kwargs = {
            "zaaktype": {
                "lookup_field": "uuid",
                "view_name": "catalogi:zaaktype-detail",
            },
        }


class InformatieObjectTypeAutorisatieSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Autorisatie
        fields = ("informatieobjecttype", "max_vertrouwelijkheidaanduiding")
        extra_kwargs = {
            "informatieobjecttype": {
                "lookup_field": "uuid",
                "view_name": "catalogi:informatieobjecttype-detail",
            },
        }


class BesluitTypeAutorisatieSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Autorisatie
        fields = ("besluittype",)
        extra_kwargs = {
            "besluittype": {
                "lookup_field": "uuid",
                "view_name": "catalogi:besluittype-detail",
            },
        }


class AutorisatieBaseSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field="component",
        mapping={
            ComponentTypes.zrc: ZaakTypeAutorisatieSerializer(),
            ComponentTypes.drc: InformatieObjectTypeAutorisatieSerializer(),
            ComponentTypes.brc: BesluitTypeAutorisatieSerializer(),
            ComponentTypes.nrc: (),
            ComponentTypes.ztc: (),
            ComponentTypes.ac: (),
        },
    )

    component_weergave = serializers.CharField(
        source="get_component_display",
        read_only=True,
        help_text=_("Omschrijving van `component`."),
    )

    class Meta:
        model = Autorisatie
        fields = ("component", "component_weergave", "scopes")
        extra_kwargs = {
            "scopes": {
                "allow_empty": True,
                "help_text": _(
                    "Lijst van scope labels. Elke scope geeft toegang tot een "
                    "set van acties/operaties, zoals gedocumenteerd bij de "
                    "betreffende component."
                ),
            }
        }
        validators = [AutorisatieValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(ComponentTypes)
        current_help = self.fields["component"].help_text or ""
        self.fields["component"].help_text = (
            current_help + f"\n\n{value_display_mapping}"
        )


class ApplicatieSerializer(serializers.HyperlinkedModelSerializer):
    autorisaties = AutorisatieBaseSerializer(many=True, required=False)

    class Meta:
        model = Applicatie
        fields = (
            "url",
            "client_ids",
            "label",
            "heeft_alle_autorisaties",
            "autorisaties",
        )
        extra_kwargs = {
            "url": {
                "lookup_field": "uuid",
                "view_name": "autorisaties:applicatie-detail",
            },
            "heeft_alle_autorisaties": {"required": False},
            "client_ids": {
                "validators": [UniqueClientIDValidator()],
                "help_text": _(
                    "Lijst van consumer identifiers (hun 'client_id'). Een "
                    "`client_id` mag slechts bij één applicatie-object voorkomen."
                ),
            },
        }

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        # either autorisaties or heeft_alle_autorisaties can be specified
        autorisaties_obj = None
        heeft_alle_autorisaties_obj = None
        # in case of update:
        if self.instance:
            autorisaties_obj = self.instance.autorisaties.all()
            heeft_alle_autorisaties_obj = self.instance.heeft_alle_autorisaties

        autorisaties = validated_attrs.get("autorisaties", autorisaties_obj)
        heeft_alle_autorisaties = validated_attrs.get(
            "heeft_alle_autorisaties", heeft_alle_autorisaties_obj
        )

        if autorisaties and heeft_alle_autorisaties is True:
            raise serializers.ValidationError(
                _("Either autorisaties or heeft_alle_autorisaties can be specified"),
                code="ambiguous-authorizations-specified",
            )

        if not autorisaties and heeft_alle_autorisaties is not True:
            raise serializers.ValidationError(
                _("Either autorisaties or heeft_alle_autorisaties should be specified"),
                code="missing-authorizations",
            )

        return validated_attrs

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
                        type_field: type,
                    }
                )
                for type in types
            ]

        serializer = AutorisatieBaseSerializer(
            virtual_autorisaties, many=True, context=self.context
        )
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
        autorisaties_data = validated_data.pop("autorisaties", None)
        applicatie = super().create(validated_data)

        if autorisaties_data:
            for auth in autorisaties_data:
                Autorisatie.objects.create(**auth, applicatie=applicatie)
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
                "updating_applicatie_via_api_deleting_existing_catalogusautorisaties",
            )
            instance.catalogusautorisatie_set.all().delete()

        autorisaties_data = validated_data.pop("autorisaties", None)
        applicatie = super().update(instance, validated_data)

        # in case of update autorisaties - remove all related autorisaties
        if autorisaties_data is not None:
            applicatie.autorisaties.all().delete()
            for auth in autorisaties_data:
                Autorisatie.objects.create(**auth, applicatie=applicatie)

        self.create_missing_credentials(applicatie)

        return applicatie


class ApplicatieUuidSerializer(ApplicatieSerializer):
    """
    Serializer for saving data in local auth DB
    uuid is used for synchronizing identifiers with AC DB
    """

    class Meta(ApplicatieSerializer.Meta):
        fields = ApplicatieSerializer.Meta.fields + ("uuid",)
