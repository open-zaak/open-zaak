# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.constants import ZaakobjectTypes
from vng_api_common.polymorphism import Discriminator, PolymorphicSerializer
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import IsImmutableValidator, URLValidator

from openzaak.components.zaken.validators import CorrectZaaktypeValidator
from openzaak.utils.auth import get_auth
from openzaak.utils.validators import (
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
)

from ...models import ZaakObject
from ..validators import (
    EitherFieldRequiredValidator,
    JQExpressionValidator,
    ObjectTypeOverigeDefinitieValidator,
    ZaakArchiefStatusValidator,
)
from .address import ObjectAdresSerializer
from .betrokkenen import (
    MedewerkerIdentificatieSerializer,
    NatuurlijkPersoonIdentificatieSerializer,
    NietNatuurlijkPersoonIdentificatieSerializer,
    OrganisatorischeEenheidIdentificatieSerializer,
    VestigingIdentificatieSerializer,
)
from .objecten import (
    ObjectBuurtSerializer,
    ObjectGemeentelijkeOpenbareRuimteSerializer,
    ObjectGemeenteSerializer,
    ObjectHuishoudenSerializer,
    ObjectInrichtingselementSerializer,
    ObjectKadastraleOnroerendeZaakSerializer,
    ObjectKunstwerkdeelSerializer,
    ObjectMaatschappelijkeActiviteitSerializer,
    ObjectOpenbareRuimteSerializer,
    ObjectOverigeSerializer,
    ObjectPandSerializer,
    ObjectSpoorbaandeelSerializer,
    ObjectTerreindeelSerializer,
    ObjectTerreinGebouwdObjectSerializer,
    ObjectWaterdeelSerializer,
    ObjectWegdeelSerializer,
    ObjectWijkSerializer,
    ObjectWoonplaatsSerializer,
    ObjectWozDeelobjectSerializer,
    ObjectWozObjectSerializer,
    ObjectWozWaardeSerializer,
    ObjectZakelijkRechtSerializer,
)


class ObjectTypeOverigeDefinitieSerializer(serializers.Serializer):
    url = serializers.URLField(
        label="Objecttype-URL",
        max_length=1000,
        help_text=(
            "URL-referentie naar de objecttype resource in een API. Deze resource "
            "moet de [JSON-schema](https://json-schema.org/)-definitie van het objecttype "
            "bevatten."
        ),
    )
    schema = serializers.CharField(
        label="schema-pad",
        max_length=100,
        help_text=(
            "Een geldige [jq](http://stedolan.github.io/jq/) expressie. Dit wordt "
            "gecombineerd met de resource uit het `url`-attribuut om het schema "
            "van het objecttype uit te lezen. Bijvoorbeeld: `.jsonSchema`."
        ),
        validators=[JQExpressionValidator()],
    )
    object_data = serializers.CharField(
        label="objectgegevens-pad",
        max_length=100,
        help_text=(
            "Een geldige [jq](http://stedolan.github.io/jq/) expressie. Dit wordt "
            "gecombineerd met de JSON data uit de OBJECT url om de objectgegevens uit "
            "te lezen en de vorm van de gegevens tegen het schema te valideren. "
            "Bijvoorbeeld: `.record.data`."
        ),
        validators=[JQExpressionValidator()],
    )


class ZaakObjectSerializer(PolymorphicSerializer):
    discriminator = Discriminator(
        discriminator_field="object_type",
        mapping={
            ZaakobjectTypes.adres: ObjectAdresSerializer(),
            ZaakobjectTypes.besluit: None,
            ZaakobjectTypes.buurt: ObjectBuurtSerializer(),
            ZaakobjectTypes.enkelvoudig_document: None,
            ZaakobjectTypes.gemeente: ObjectGemeenteSerializer(),
            ZaakobjectTypes.gemeentelijke_openbare_ruimte: ObjectGemeentelijkeOpenbareRuimteSerializer(),
            ZaakobjectTypes.huishouden: ObjectHuishoudenSerializer(),
            ZaakobjectTypes.inrichtingselement: ObjectInrichtingselementSerializer(),
            ZaakobjectTypes.kadastrale_onroerende_zaak: ObjectKadastraleOnroerendeZaakSerializer(),
            ZaakobjectTypes.kunstwerkdeel: ObjectKunstwerkdeelSerializer(),
            ZaakobjectTypes.maatschappelijke_activiteit: ObjectMaatschappelijkeActiviteitSerializer(),
            ZaakobjectTypes.medewerker: MedewerkerIdentificatieSerializer(),
            ZaakobjectTypes.natuurlijk_persoon: NatuurlijkPersoonIdentificatieSerializer(),
            ZaakobjectTypes.niet_natuurlijk_persoon: NietNatuurlijkPersoonIdentificatieSerializer(),
            ZaakobjectTypes.openbare_ruimte: ObjectOpenbareRuimteSerializer(),
            ZaakobjectTypes.organisatorische_eenheid: OrganisatorischeEenheidIdentificatieSerializer(),
            ZaakobjectTypes.pand: ObjectPandSerializer(),
            ZaakobjectTypes.spoorbaandeel: ObjectSpoorbaandeelSerializer(),
            ZaakobjectTypes.status: None,
            ZaakobjectTypes.terreindeel: ObjectTerreindeelSerializer(),
            ZaakobjectTypes.terrein_gebouwd_object: ObjectTerreinGebouwdObjectSerializer(),
            ZaakobjectTypes.vestiging: VestigingIdentificatieSerializer(),
            ZaakobjectTypes.waterdeel: ObjectWaterdeelSerializer(),
            ZaakobjectTypes.wegdeel: ObjectWegdeelSerializer(),
            ZaakobjectTypes.wijk: ObjectWijkSerializer(),
            ZaakobjectTypes.woonplaats: ObjectWoonplaatsSerializer(),
            ZaakobjectTypes.woz_deelobject: ObjectWozDeelobjectSerializer(),
            ZaakobjectTypes.woz_object: ObjectWozObjectSerializer(),
            ZaakobjectTypes.woz_waarde: ObjectWozWaardeSerializer(),
            ZaakobjectTypes.zakelijk_recht: ObjectZakelijkRechtSerializer(),
            ZaakobjectTypes.overige: ObjectOverigeSerializer(),
        },
        group_field="object_identificatie",
        same_model=False,
    )
    object_type_overige_definitie = ObjectTypeOverigeDefinitieSerializer(
        label=_("definitie object type overige"),
        required=False,
        allow_null=True,
        help_text=(
            "Verwijzing naar het schema van het type OBJECT als `objectType` de "
            'waarde "overige" heeft.\n\n'
            "* De URL referentie moet naar een JSON endpoint "
            "  wijzen waarin het objecttype gedefinieerd is, inclusief het "
            "  [JSON-schema](https://json-schema.org/).\n"
            "* Gebruik het `schema` attribuut om te verwijzen naar het schema binnen "
            "  de objecttype resource (deze gebruikt het "
            "  [jq](http://stedolan.github.io/jq/) formaat.\n"
            "* Gebruik het `objectData` attribuut om te verwijzen naar de gegevens "
            "  binnen het OBJECT. Deze gebruikt ook het "
            "  [jq](http://stedolan.github.io/jq/) formaat."
            "\n\nIndien je hier gebruikt van maakt, dan moet je een OBJECT url opgeven "
            "en is het gebruik van objectIdentificatie niet mogelijk. "
            "De opgegeven OBJECT url wordt gevalideerd tegen het schema van het "
            "opgegeven objecttype."
        ),
    )

    class Meta:
        model = ZaakObject
        fields = (
            "url",
            "uuid",
            "zaak",
            "object",
            "zaakobjecttype",
            "object_type",
            "object_type_overige",
            "object_type_overige_definitie",
            "relatieomschrijving",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "uuid": {"read_only": True},
            "zaak": {"lookup_field": "uuid", "validators": [IsImmutableValidator()]},
            "object": {
                "required": False,
                "validators": [URLValidator(get_auth=get_auth), IsImmutableValidator()],
            },
            "object_type": {
                "validators": [IsImmutableValidator()],
            },
            "zaakobjecttype": {
                "lookup_field": "uuid",
                "max_length": 1000,
                "allow_null": False,
                "allow_blank": True,
                "validators": [
                    LooseFkResourceValidator(
                        "ZaakObjectType", settings.ZTC_API_STANDARD
                    ),
                    LooseFkIsImmutableValidator(),
                ],
            },
        }
        validators = [
            EitherFieldRequiredValidator(
                fields=("object", "object_identificatie"),
                message=_("object or objectIdentificatie must be provided"),
                code="invalid-zaakobject",
                skip_for_updates=True,
            ),
            ObjectTypeOverigeDefinitieValidator(),
            ZaakArchiefStatusValidator(),
            CorrectZaaktypeValidator("zaakobjecttype"),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(ZaakobjectTypes)
        fields["object_type"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate(self, attrs):
        validated_attrs = super().validate(attrs)

        # for update don't validate fields, cause most of them are immutable
        if self.instance:
            return validated_attrs

        object_type = validated_attrs.get("object_type", None)
        object_type_overige = validated_attrs.get("object_type_overige", None)
        object_type_overige_definitie = validated_attrs.get(
            "object_type_overige_definitie", None
        )

        if object_type == ZaakobjectTypes.overige and not (
            object_type_overige or object_type_overige_definitie
        ):
            raise serializers.ValidationError(
                _(
                    'Als `objectType` de waarde "overige" heeft, moet '
                    "`objectTypeOverige` of `objectTypeOverigeDefinitie` van een "
                    "waarde voorzien zijn."
                ),
                code="missing-object-type-overige",
            )

        if object_type != ZaakobjectTypes.overige and object_type_overige:
            raise serializers.ValidationError(
                _(
                    'Als `objectType` niet de waarde "overige" heeft, mag '
                    "`objectTypeOverige` niet van een waarde voorzien zijn."
                ),
                code="invalid-object-type-overige-usage",
            )

        return validated_attrs

    def to_internal_value(self, data):
        # add object_type to data for PATCH
        if self.instance and "object_type" not in data:
            data["object_type"] = self.instance.object_type

        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        group_data = validated_data.pop("object_identificatie", None)
        zaakobject = super().create(validated_data)

        if group_data:
            group_serializer = self.discriminator.mapping[validated_data["object_type"]]
            serializer = group_serializer.get_fields()["object_identificatie"]
            group_data["zaakobject"] = zaakobject
            serializer.create(group_data)

        return zaakobject

    @transaction.atomic
    def update(self, instance, validated_data):
        group_data = validated_data.pop("object_identificatie", None)
        zaakobject = super().update(instance, validated_data)

        if group_data:
            group_serializer = self.discriminator.mapping[instance.object_type]
            serializer = group_serializer.get_fields()["object_identificatie"]
            # remove the previous data
            model = serializer.Meta.model
            model.objects.filter(zaakobject=zaakobject).delete()

            group_data["zaakobject"] = zaakobject
            serializer.create(group_data)

        return zaakobject
