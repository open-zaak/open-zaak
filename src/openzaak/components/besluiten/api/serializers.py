# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Serializers of the Besluit Registratie Component REST API
"""
from django.conf import settings
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.virtual_models import ProxyMixin
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.utils import get_help_text
from vng_api_common.validators import IsImmutableValidator, validate_rsin

from openzaak.components.documenten.api.fields import EnkelvoudigInformatieObjectField
from openzaak.components.zaken.api.utils import (
    create_remote_zaakbesluit,
    delete_remote_zaakbesluit,
)
from openzaak.utils.api import create_remote_oio
from openzaak.utils.validators import (
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
    ObjecttypeInformatieobjecttypeRelationValidator,
    PublishValidator,
)

from ..constants import VervalRedenen
from ..models import Besluit, BesluitInformatieObject
from .validators import BesluittypeZaaktypeValidator, UniekeIdentificatieValidator


class BesluitSerializer(serializers.HyperlinkedModelSerializer):
    vervalreden_weergave = serializers.CharField(
        source="get_vervalreden_display", read_only=True
    )

    class Meta:
        model = Besluit
        fields = (
            "url",
            "identificatie",
            "verantwoordelijke_organisatie",
            "besluittype",
            "zaak",
            "datum",
            "toelichting",
            "bestuursorgaan",
            "ingangsdatum",
            "vervaldatum",
            "vervalreden",
            "vervalreden_weergave",
            "publicatiedatum",
            "verzenddatum",
            "uiterlijke_reactiedatum",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            # per BRC API spec!
            "besluittype": {
                "lookup_field": "uuid",
                "max_length": 200,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator("BesluitType", settings.ZTC_API_SPEC),
                    LooseFkIsImmutableValidator(),
                    PublishValidator(),
                ],
            },
            # per BRC API spec!
            "zaak": {"lookup_field": "uuid", "max_length": 200},
            "identificatie": {"validators": [IsImmutableValidator()]},
            "verantwoordelijke_organisatie": {
                "validators": [IsImmutableValidator(), validate_rsin]
            },
        }
        validators = [UniekeIdentificatieValidator(), BesluittypeZaaktypeValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(VervalRedenen)
        self.fields["vervalreden"].help_text += f"\n\n{value_display_mapping}"

    def create_zaakbesluit(self, besluit):
        zaak_url = self.initial_data["zaak"]
        besluit_url = reverse(
            "besluit-detail",
            kwargs={
                "version": settings.REST_FRAMEWORK["DEFAULT_VERSION"],
                "uuid": besluit.uuid,
            },
            request=self.context["request"],
        )
        return create_remote_zaakbesluit(besluit_url, zaak_url)

    def create(self, validated_data):
        besluit = super().create(validated_data)

        # local FK - nothing to do -> our signals create the ZaakBesluit
        if not isinstance(besluit.zaak, ProxyMixin):
            return besluit

        # manual transaction management - zaken API checks that the Besluit
        # exists, so that transaction must be committed.
        # If it fails in any other way, we need to handle that by rolling back
        # the Besluit creation.
        try:
            response = self.create_zaakbesluit(besluit)
        except Exception as exception:
            besluit.delete()
            raise serializers.ValidationError(
                {"zaak": _("Could not create remote relation: {}".format(exception))},
                code="pending-relations",
            )
        else:
            besluit._zaakbesluit_url = response["url"]
            besluit.save()
        return besluit

    @transaction.atomic
    def update(self, instance, validated_data):
        besluit = super().update(instance, validated_data)

        if besluit.zaak == besluit.previous_zaak:
            return besluit

        if isinstance(besluit.previous_zaak, ProxyMixin) and besluit._zaakbesluit_url:
            try:
                delete_remote_zaakbesluit(besluit._zaakbesluit_url)
            except Exception as exception:
                raise serializers.ValidationError(
                    {
                        "zaak": _(
                            "Could not delete remote relation: {}".format(exception)
                        )
                    },
                    code="pending-relations",
                )

        if isinstance(besluit.zaak, ProxyMixin):
            try:
                response = self.create_zaakbesluit(besluit)
            except Exception as exception:
                raise serializers.ValidationError(
                    {
                        "zaak": _(
                            "Could not create remote relation: {}".format(exception)
                        )
                    },
                    code="pending-relations",
                )
            else:
                besluit._zaakbesluit_url = response["url"]
                besluit.save()

        return besluit


class BesluitInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectField(
        validators=[
            LooseFkIsImmutableValidator(instance_path="canonical"),
            LooseFkResourceValidator(
                "EnkelvoudigInformatieObject", settings.DRC_API_SPEC
            ),
        ],
        max_length=1000,
        min_length=1,
        help_text=get_help_text(
            "besluiten.BesluitInformatieObject", "informatieobject"
        ),
    )

    class Meta:
        model = BesluitInformatieObject
        fields = ("url", "informatieobject", "besluit")
        validators = [
            UniqueTogetherValidator(
                queryset=BesluitInformatieObject.objects.all(),
                fields=["besluit", "informatieobject"],
            ),
            ObjecttypeInformatieobjecttypeRelationValidator("besluit", "besluittype"),
        ]
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "besluit": {"lookup_field": "uuid", "validators": [IsImmutableValidator()]},
        }

    def create(self, validated_data):
        with transaction.atomic():
            bio = super().create(validated_data)

        # local FK or CMIS - nothing to do -> our signals create the OIO
        if bio.informatieobject.pk or settings.CMIS_ENABLED:
            return bio

        # we know that we got valid URLs in the initial data
        io_url = self.initial_data["informatieobject"]
        besluit_url = self.initial_data["besluit"]

        # manual transaction management - documents API checks that the BIO
        # exists, so that transaction must be committed.
        # If it fails in any other way, we need to handle that by rolling back
        # the BIO creation.
        try:
            response = create_remote_oio(io_url, besluit_url, "besluit")
        except Exception as exception:
            bio.delete()
            raise serializers.ValidationError(
                {
                    "informatieobject": _(
                        "Could not create remote relation: {exception}"
                    ).format(exception=exception)
                },
                code="pending-relations",
            )
        else:
            bio._objectinformatieobject_url = response["url"]
            bio.save()
        return bio

    def run_validators(self, value):
        """
        Add read_only fields with defaults to value before running validators.
        """
        # In the case CMIS is enabled, we need to filter on the URL and not the canonical object
        if value.get("informatieobject") is not None and settings.CMIS_ENABLED:
            value["informatieobject"] = self.initial_data.get("informatieobject")

        return super().run_validators(value)
