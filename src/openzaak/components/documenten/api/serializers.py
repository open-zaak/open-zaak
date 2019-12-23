"""
Serializers of the Document Registratie Component REST API
"""
import uuid

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.drf import FKOrURLField
from drf_extra_fields.fields import Base64FileField
from humanize import naturalsize
from privates.storages import PrivateMediaFileSystemStorage
from rest_framework import serializers
from rest_framework.reverse import reverse
from vng_api_common.constants import ObjectTypes, VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    add_choice_values_help_text,
)
from vng_api_common.utils import get_help_text

from openzaak.components.besluiten.models import Besluit
from openzaak.components.zaken.models import Zaak
from openzaak.utils.serializer_fields import LengthHyperlinkedRelatedField
from openzaak.utils.validators import (
    IsImmutableValidator,
    LooseFkIsImmutableValidator,
    LooseFkResourceValidator,
    PublishValidator,
)

from ..constants import ChecksumAlgoritmes, OndertekeningSoorten, Statussen
from ..models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from .validators import InformatieObjectUniqueValidator, StatusValidator


class AnyFileType:
    def __contains__(self, item):
        return True


class AnyBase64File(Base64FileField):
    ALLOWED_TYPES = AnyFileType()

    def __init__(self, view_name: str = None, *args, **kwargs):
        self.view_name = view_name
        super().__init__(*args, **kwargs)

    def get_file_extension(self, filename, decoded_file):
        return "bin"

    def to_representation(self, file):
        is_private_storage = isinstance(file.storage, PrivateMediaFileSystemStorage)

        if not is_private_storage or self.represent_in_base64:
            return super().to_representation(file)

        assert (
            self.view_name
        ), "You must pass the `view_name` kwarg for private media fields"

        model_instance = file.instance
        request = self.context.get("request")

        url_field = self.parent.fields["url"]
        lookup_field = url_field.lookup_field
        kwargs = {lookup_field: getattr(model_instance, lookup_field)}
        url = reverse(self.view_name, kwargs=kwargs, request=request)

        # Retrieve the correct version to construct the download url that
        # points to the content of that version
        instance = self.parent.instance
        # in case of pagination instance can be a list object
        if isinstance(instance, list):
            instance = instance[0]

        if hasattr(instance, "versie"):
            versie = instance.versie
        else:
            versie = instance.get(uuid=kwargs["uuid"]).versie
        query_string = urlencode({"versie": versie})
        return f"{url}?{query_string}"


class IntegriteitSerializer(GegevensGroepSerializer):
    class Meta:
        model = EnkelvoudigInformatieObject
        gegevensgroep = "integriteit"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(ChecksumAlgoritmes)
        self.fields["algoritme"].help_text += f"\n\n{value_display_mapping}"


class OndertekeningSerializer(GegevensGroepSerializer):
    class Meta:
        model = EnkelvoudigInformatieObject
        gegevensgroep = "ondertekening"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(OndertekeningSoorten)
        self.fields["soort"].help_text += f"\n\n{value_display_mapping}"


class EnkelvoudigInformatieObjectHyperlinkedRelatedField(LengthHyperlinkedRelatedField):
    """
    Custom field to construct the url for models that have a ForeignKey to
    `EnkelvoudigInformatieObject`

    Needed because the canonical `EnkelvoudigInformatieObjectCanonical` no longer stores
    the uuid, but the `EnkelvoudigInformatieObject`s related to it do
    store the uuid
    """

    def get_url(self, obj, view_name, request, format):
        obj_latest_version = obj.latest_version
        return super().get_url(obj_latest_version, view_name, request, format)

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_value = view_kwargs[self.lookup_url_kwarg]
        lookup_kwargs = {self.lookup_field: lookup_value}
        try:
            return (
                self.get_queryset()
                .filter(**lookup_kwargs)
                .order_by("-versie")
                .first()
                .canonical
            )
        except (TypeError, AttributeError):
            self.fail("does_not_exist")


class EnkelvoudigInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for the EnkelvoudigInformatieObject model
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="enkelvoudiginformatieobject-detail", lookup_field="uuid"
    )
    inhoud = AnyBase64File(
        view_name="enkelvoudiginformatieobject-download",
        help_text=_(
            f"Minimal accepted size of uploaded file = {settings.MIN_UPLOAD_SIZE} bytes "
            f"(or {naturalsize(settings.MIN_UPLOAD_SIZE, binary=True)})"
        ),
    )
    bestandsomvang = serializers.IntegerField(
        source="inhoud.size",
        read_only=True,
        min_value=0,
        help_text=_("Aantal bytes dat de inhoud van INFORMATIEOBJECT in beslag neemt."),
    )
    integriteit = IntegriteitSerializer(
        label=_("integriteit"),
        allow_null=True,
        required=False,
        help_text=_(
            "Uitdrukking van mate van volledigheid en onbeschadigd zijn van digitaal bestand."
        ),
    )
    # TODO: validator!
    ondertekening = OndertekeningSerializer(
        label=_("ondertekening"),
        allow_null=True,
        required=False,
        help_text=_(
            "Aanduiding van de rechtskracht van een informatieobject. Mag niet van een waarde "
            "zijn voorzien als de `status` de waarde 'in bewerking' of 'ter vaststelling' heeft."
        ),
    )
    locked = serializers.BooleanField(
        label=_("locked"),
        read_only=True,
        source="canonical.lock",
        help_text=_(
            "Geeft aan of het document gelocked is. Alleen als een document gelocked is, "
            "mogen er aanpassingen gemaakt worden."
        ),
    )

    class Meta:
        model = EnkelvoudigInformatieObject
        fields = (
            "url",
            "identificatie",
            "bronorganisatie",
            "creatiedatum",
            "titel",
            "vertrouwelijkheidaanduiding",
            "auteur",
            "status",
            "formaat",
            "taal",
            "versie",
            "begin_registratie",
            "bestandsnaam",
            "inhoud",
            "bestandsomvang",
            "link",
            "beschrijving",
            "ontvangstdatum",
            "verzenddatum",
            "indicatie_gebruiksrecht",
            "ondertekening",
            "integriteit",
            "informatieobjecttype",  # van-relatie,
            "locked",
        )
        extra_kwargs = {
            "taal": {"min_length": 3},
            "informatieobjecttype": {
                "lookup_field": "uuid",
                "max_length": 200,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator(
                        "InformatieObjectType", settings.ZTC_API_SPEC
                    ),
                    LooseFkIsImmutableValidator(),
                    PublishValidator(),
                ],
            },
        }
        read_only_fields = ["versie", "begin_registratie"]
        validators = [StatusValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        self.fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Statussen)
        self.fields["status"].help_text += f"\n\n{value_display_mapping}"

    def validate_indicatie_gebruiksrecht(self, indicatie):
        if (
            self.instance
            and not indicatie
            and self.instance.canonical.gebruiksrechten_set.exists()
        ):
            raise serializers.ValidationError(
                _(
                    "De indicatie kan niet weggehaald worden of ongespecifieerd "
                    "zijn als er Gebruiksrechten gedefinieerd zijn."
                ),
                code="existing-gebruiksrechten",
            )
        # create: not self.instance or update: usage_rights exists
        elif indicatie and (
            not self.instance
            or not self.instance.canonical.gebruiksrechten_set.exists()
        ):
            raise serializers.ValidationError(
                _(
                    "De indicatie moet op 'ja' gezet worden door `gebruiksrechten` "
                    "aan te maken, dit kan niet direct op deze resource."
                ),
                code="missing-gebruiksrechten",
            )
        return indicatie

    @transaction.atomic
    def create(self, validated_data):
        """
        Handle nested writes.
        """
        integriteit = validated_data.pop("integriteit", None)
        ondertekening = validated_data.pop("ondertekening", None)
        # add vertrouwelijkheidaanduiding
        if "vertrouwelijkheidaanduiding" not in validated_data:
            informatieobjecttype = validated_data["informatieobjecttype"]
            validated_data[
                "vertrouwelijkheidaanduiding"
            ] = informatieobjecttype.vertrouwelijkheidaanduiding

        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()
        validated_data["canonical"] = canonical

        eio = super().create(validated_data)
        eio.integriteit = integriteit
        eio.ondertekening = ondertekening
        eio.save()
        return eio

    def update(self, instance, validated_data):
        """
        Instead of updating an existing EnkelvoudigInformatieObject,
        create a new EnkelvoudigInformatieObject with the same
        EnkelvoudigInformatieObjectCanonical
        """
        instance.integriteit = validated_data.pop("integriteit", None)
        instance.ondertekening = validated_data.pop("ondertekening", None)

        validated_data_field_names = validated_data.keys()
        for field in instance._meta.get_fields():
            if field.name not in validated_data_field_names:
                validated_data[field.name] = getattr(instance, field.name)

        validated_data["pk"] = None
        validated_data["versie"] += 1

        # Remove the lock from the data from which a new
        # EnkelvoudigInformatieObject will be created, because lock is not a
        # part of that model
        validated_data.pop("lock")

        return super().create(validated_data)


class EnkelvoudigInformatieObjectWithLockSerializer(
    EnkelvoudigInformatieObjectSerializer
):
    """
    This serializer class is used by EnkelvoudigInformatieObjectViewSet for
    update and partial_update operations
    """

    lock = serializers.CharField(
        write_only=True,
        help_text="Tijdens het updaten van een document (PATCH, PUT) moet het "
        "`lock` veld opgegeven worden. Bij het aanmaken (POST) mag "
        "het geen waarde hebben.",
    )

    class Meta(EnkelvoudigInformatieObjectSerializer.Meta):
        # Use the same fields as the parent class and add the lock to it
        fields = EnkelvoudigInformatieObjectSerializer.Meta.fields + ("lock",)

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)

        if not self.instance.canonical.lock:
            raise serializers.ValidationError(
                _("Unlocked document can't be modified"), code="unlocked"
            )

        try:
            lock = valid_attrs["lock"]
        except KeyError:
            raise serializers.ValidationError(
                _("Lock id must be provided"), code="missing-lock-id"
            )

        # update
        if lock != self.instance.canonical.lock:
            raise serializers.ValidationError(
                _("Lock id is not correct"), code="incorrect-lock-id"
            )
        return valid_attrs


class LockEnkelvoudigInformatieObjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the lock action of EnkelvoudigInformatieObjectCanonical
    model
    """

    class Meta:
        model = EnkelvoudigInformatieObjectCanonical
        fields = ("lock",)
        extra_kwargs = {"lock": {"read_only": True}}

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)
        if self.instance.lock:
            raise serializers.ValidationError(
                _("The document is already locked"), code="existing-lock"
            )
        return valid_attrs

    def save(self, **kwargs):
        self.instance.lock = uuid.uuid4().hex
        self.instance.save()

        return self.instance


class UnlockEnkelvoudigInformatieObjectSerializer(serializers.ModelSerializer):
    """
    Serializer for the unlock action of EnkelvoudigInformatieObjectCanonical
    model
    """

    class Meta:
        model = EnkelvoudigInformatieObjectCanonical
        fields = ("lock",)
        extra_kwargs = {"lock": {"required": False, "write_only": True}}

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)
        force_unlock = self.context.get("force_unlock", False)

        if force_unlock:
            return valid_attrs

        lock = valid_attrs.get("lock", "")
        if lock != self.instance.lock:
            raise serializers.ValidationError(
                _("Lock id is not correct"), code="incorrect-lock-id"
            )
        return valid_attrs

    def save(self, **kwargs):
        self.instance.lock = ""
        self.instance.save()
        return self.instance


class GebruiksrechtenSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name="enkelvoudiginformatieobject-detail",
        lookup_field="uuid",
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text("documenten.Gebruiksrechten", "informatieobject"),
    )

    class Meta:
        model = Gebruiksrechten
        fields = (
            "url",
            "informatieobject",
            "startdatum",
            "einddatum",
            "omschrijving_voorwaarden",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "informatieobject": {"validators": [IsImmutableValidator()]},
        }


class ObjectInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name="enkelvoudiginformatieobject-detail",
        lookup_field="uuid",
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text(
            "documenten.ObjectInformatieObject", "informatieobject"
        ),
    )
    object = FKOrURLField(
        max_length=1000,
        min_length=1,
        help_text=_(
            "URL-referentie naar het gerelateerde OBJECT (in deze of een andere API)."
        ),
    )

    class Meta:
        model = ObjectInformatieObject
        fields = ("url", "informatieobject", "object", "object_type")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "object": {"lookup_field": "uuid"},
        }
        validators = [InformatieObjectUniqueValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(ObjectTypes)
        self.fields["object_type"].help_text += f"\n\n{value_display_mapping}"

    def set_object_properties(self, object_type):
        object_field = self.fields["object"]

        if object_type == "besluit":
            object_field.source = "besluit"
            object_field.validators.append(
                LooseFkResourceValidator("Besluit", settings.BRC_API_SPEC)
            )
        else:
            object_field.source = "zaak"
            object_field.validators.append(
                LooseFkResourceValidator("Zaak", settings.ZRC_API_SPEC)
            )

    def to_internal_value(self, data):
        object_type = data["object_type"]
        self.set_object_properties(object_type)
        res = super().to_internal_value(data)
        return res

    def to_representation(self, instance):
        object_type = instance.object_type
        self.set_object_properties(object_type)
        return super().to_representation(instance)

    def create(self, validated_data):
        object_type = validated_data["object_type"]
        validated_data[object_type] = validated_data.pop("object")

        oio = super().create(validated_data)
        return oio
