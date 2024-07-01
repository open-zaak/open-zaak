# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Serializers of the Document Registratie Component REST API
"""
import binascii
import math
import uuid
from base64 import b64decode
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.db import transaction
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from drc_cmis.utils.convert import make_absolute_uri
from drf_extra_fields.fields import Base64FileField
from humanize import naturalsize
from privates.storages import PrivateMediaFileSystemStorage
from rest_framework import serializers
from rest_framework.reverse import reverse
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)
from vng_api_common.utils import get_help_text

from openzaak.contrib.verzoeken.validators import verzoek_validator
from openzaak.utils.serializer_fields import (
    FKOrServiceUrlField,
    LengthHyperlinkedRelatedField,
)
from openzaak.utils.serializers import get_from_serializer_data_or_instance
from openzaak.utils.validators import (
    IsImmutableValidator,
    LooseFkResourceValidator,
    PublishValidator,
)

from ..constants import (
    ChecksumAlgoritmes,
    ObjectInformatieObjectTypes,
    OndertekeningSoorten,
    Statussen,
)
from ..models import (
    BestandsDeel,
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
    Verzending,
)
from ..query.cmis import flatten_gegevens_groep
from ..utils import PrivateMediaStorageWithCMIS
from .fields import OnlyRemoteOrFKOrURLField
from .utils import create_filename, merge_files
from .validators import (
    InformatieObjectUniqueValidator,
    StatusValidator,
    UniekeIdentificatieValidator,
    VerzendingAddressValidator,
)

oz = "openzaak.components"


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

    def to_internal_value(self, base64_data):
        try:
            return super().to_internal_value(base64_data)
        except Exception:
            try:
                # If validate is False, no check is done to see if the data contains non base-64 alphabet characters
                b64decode(base64_data, validate=True)
            except binascii.Error as e:
                if str(e) == "Incorrect padding":
                    raise ValidationError(
                        _("The provided base64 data has incorrect padding"),
                        code="incorrect-base64-padding",
                    )
                raise ValidationError(str(e), code="invalid-base64")
            except TypeError as exc:
                raise ValidationError(str(exc))

    def to_representation(self, file):
        is_private_storage = isinstance(file.storage, PrivateMediaFileSystemStorage)
        is_cmis_storage = isinstance(file.storage, PrivateMediaStorageWithCMIS)

        if not (is_private_storage or is_cmis_storage) or self.represent_in_base64:
            return super().to_representation(file)

        # if there is no associated file link is not returned
        try:
            file.file
        except ValueError:
            return None

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

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(ChecksumAlgoritmes)
        fields["algoritme"].help_text += f"\n\n{value_display_mapping}"

        return fields


class OndertekeningSerializer(GegevensGroepSerializer):
    class Meta:
        model = EnkelvoudigInformatieObject
        gegevensgroep = "ondertekening"

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(OndertekeningSoorten)
        fields["soort"].help_text += f"\n\n{value_display_mapping}"

        return fields


class EnkelvoudigInformatieObjectHyperlinkedRelatedField(LengthHyperlinkedRelatedField):
    """
    Custom field to construct the url for models that have a ForeignKey to
    `EnkelvoudigInformatieObject`

    Needed because the canonical `EnkelvoudigInformatieObjectCanonical` no longer stores
    the uuid, but the `EnkelvoudigInformatieObject`s related to it do
    store the uuid
    """

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

    def get_attribute(self, instance):
        return instance.get_informatieobject()


class LockField(serializers.CharField):
    def get_attribute(self, instance):
        return instance.get_current_lock_value()


class BestandsDeelSerializer(serializers.HyperlinkedModelSerializer):
    lock = LockField(
        required=True,
        help_text="Hash string, which represents id of the lock of related informatieobject",
    )

    class Meta:
        model = BestandsDeel
        fields = ("url", "volgnummer", "omvang", "inhoud", "voltooid", "lock")
        extra_kwargs = {
            "url": {
                "lookup_field": "uuid",
            },
            "volgnummer": {
                "read_only": True,
            },
            "omvang": {
                "read_only": True,
            },
            "voltooid": {
                "read_only": True,
                "help_text": _(
                    "Indicatie of dit bestandsdeel volledig is geupload. Dat wil zeggen: "
                    "het aantal bytes dat staat genoemd bij grootte is daadwerkelijk ontvangen."
                ),
            },
            "inhoud": {
                "write_only": True,
            },
        }

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)

        inhoud = valid_attrs.get("inhoud")
        lock = valid_attrs.get("lock")
        if inhoud:
            if inhoud.size != self.instance.omvang:
                raise serializers.ValidationError(
                    _(
                        "Het aangeleverde bestand heeft een afwijkende bestandsgrootte (volgens het `omvang`-veld)."
                        "Verwachting: {expected}b, ontvangen: {received}b"
                    ).format(expected=self.instance.omvang, received=inhoud.size),
                    code="file-size",
                )

        current_lock = self.instance.get_current_lock_value()
        if lock != current_lock:
            raise serializers.ValidationError(
                _("Lock id is not correct"), code="incorrect-lock-id"
            )

        return valid_attrs


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
        required=False,
        allow_null=True,
    )
    bestandsomvang = serializers.IntegerField(
        allow_null=True,
        required=False,
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
    informatieobjecttype = FKOrServiceUrlField(
        lookup_field="uuid",
        max_length=200,
        min_length=1,
        help_text=_(
            "URL-referentie naar het INFORMATIEOBJECTTYPE (in de Catalogi API)."
        ),
        validators=[
            LooseFkResourceValidator("InformatieObjectType", settings.ZTC_API_STANDARD),
            PublishValidator(),
        ],
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
    bestandsdelen = BestandsDeelSerializer(
        many=True,
        source="get_bestandsdelen",
        read_only=True,
    )

    inclusion_serializers = {
        "informatieobjecttype": f"{oz}.catalogi.api.serializers.InformatieObjectTypeSerializer",
    }

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
            "verschijningsvorm",
            "ondertekening",
            "integriteit",
            "informatieobjecttype",  # van-relatie,
            "locked",
            "bestandsdelen",
            "trefwoorden",
        )
        extra_kwargs = {
            "taal": {"min_length": 3},
            "informatieobjecttype": {
                "lookup_field": "uuid",
                "max_length": 200,
                "min_length": 1,
                "validators": [
                    LooseFkResourceValidator(
                        "InformatieObjectType", settings.ZTC_API_STANDARD
                    ),
                    PublishValidator(),
                ],
            },
            # todo mark 'deprecated' in OAS after moving to drf-spectacular
            "verzenddatum": {
                "help_text": _(
                    "**DEPRECATED** Dit attribuut is verplaatst naar resource Verzending.\n\n"
                    "De datum waarop het INFORMATIEOBJECT verzonden is, zoals deze op het "
                    "INFORMATIEOBJECT vermeld is. Dit geldt voor zowel inkomende als uitgaande "
                    "INFORMATIEOBJECTen. Eenzelfde informatieobject kan niet tegelijk inkomend "
                    "en uitgaand zijn. Ontvangst en verzending is voorbehouden aan documenten "
                    "die van of naar andere personen ontvangen of verzonden zijn waarbij die "
                    "personen niet deel uit maken van de behandeling van de zaak waarin het "
                    "document een rol speelt."
                )
            },
            "ontvangstdatum": {
                "help_text": _(
                    "**DEPRECATED** Dit attribuut is verplaatst naar resource Verzending.\n\n "
                    "De datum waarop het INFORMATIEOBJECT ontvangen is. Verplicht te registreren "
                    "voor INFORMATIEOBJECTen die van buiten de zaakbehandelende organisatie(s) "
                    "ontvangen zijn. Ontvangst en verzending is voorbehouden aan documenten die "
                    "van of naar andere personen ontvangen of verzonden zijn waarbij die personen "
                    "niet deel uit maken van de behandeling van de zaak waarin het document een rol speelt."
                )
            },
        }
        read_only_fields = ["versie", "begin_registratie"]
        validators = [
            StatusValidator(),
            UniekeIdentificatieValidator(),
        ]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(
            VertrouwelijkheidsAanduiding
        )
        fields[
            "vertrouwelijkheidaanduiding"
        ].help_text += f"\n\n{value_display_mapping}"

        value_display_mapping = add_choice_values_help_text(Statussen)
        fields["status"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate_indicatie_gebruiksrecht(self, indicatie):
        if self.instance and not indicatie and self.instance.has_gebruiksrechten():
            raise serializers.ValidationError(
                _(
                    "De indicatie kan niet weggehaald worden of ongespecifieerd "
                    "zijn als er Gebruiksrechten gedefinieerd zijn."
                ),
                code="existing-gebruiksrechten",
            )
        # create: not self.instance or update: usage_rights exists
        elif indicatie and (
            not self.instance or not self.instance.has_gebruiksrechten()
        ):
            raise serializers.ValidationError(
                _(
                    "De indicatie moet op 'ja' gezet worden door `gebruiksrechten` "
                    "aan te maken, dit kan niet direct op deze resource."
                ),
                code="missing-gebruiksrechten",
            )
        return indicatie

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)

        # check if file.size equal bestandsomvang
        if self.instance is None or not self.partial:  # create and update PUT
            if (
                valid_attrs.get("inhoud") is not None
                and "bestandsomvang" in valid_attrs
                and valid_attrs["inhoud"].size != valid_attrs["bestandsomvang"]
            ):
                raise serializers.ValidationError(
                    _(
                        "The size of upload file should match the 'bestandsomvang' field"
                    ),
                    code="file-size",
                )

            # If `bestandsomvang` is not explicitly defined, derive it from the `inhoud`
            if (
                valid_attrs.get("inhoud") is not None
                and "bestandsomvang" not in valid_attrs
            ):
                valid_attrs["bestandsomvang"] = valid_attrs["inhoud"].size
        else:  # update PATCH
            inhoud = get_from_serializer_data_or_instance("inhoud", valid_attrs, self)
            bestandsomvang = get_from_serializer_data_or_instance(
                "bestandsomvang", valid_attrs, self
            )
            if inhoud and inhoud.size != bestandsomvang:
                raise serializers.ValidationError(
                    _("The size of upload file should match bestandsomvang field"),
                    code="file-size",
                )

        return valid_attrs

    def _create_bestandsdeel(
        self,
        full_size,
        canonical: Optional[EnkelvoudigInformatieObjectCanonical] = None,
        eio_uuid: Optional[str] = None,
    ):
        """add chunk urls"""
        kwargs = (
            {"informatieobject": canonical}
            if canonical
            else {"informatieobject_uuid": eio_uuid}
        )
        parts = math.ceil(full_size / settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE)
        for i in range(parts):
            chunk_size = min(settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE, full_size)
            BestandsDeel.objects.create(omvang=chunk_size, volgnummer=i + 1, **kwargs)
            full_size -= chunk_size

    @transaction.atomic
    def create(self, validated_data):
        """
        Handle nested writes.
        """
        # add vertrouwelijkheidaanduiding
        if "vertrouwelijkheidaanduiding" not in validated_data:
            informatieobjecttype = validated_data["informatieobjecttype"]
            validated_data["vertrouwelijkheidaanduiding"] = (
                informatieobjecttype.vertrouwelijkheidaanduiding
            )

        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()
        validated_data["canonical"] = canonical

        # pass the request so possible adapters can use this to build fully qualified
        # absolute URLs
        validated_data["_request"] = self.context.get("request")

        integriteit = (
            validated_data.pop("integriteit", {}) or {}
        )  # integriteit and ondertekening can also be set to None
        ondertekening = validated_data.pop("ondertekening", {}) or {}

        if settings.CMIS_ENABLED:
            # The fields integriteit and ondertekening are of "GegevensGroepType", so they need to be
            # flattened before sending to the DMS
            flat_integriteit = flatten_gegevens_groep(integriteit, "integriteit")
            flat_ondertekening = flatten_gegevens_groep(ondertekening, "ondertekening")

            validated_data.update(**flat_integriteit, **flat_ondertekening)

        eio = super().create(validated_data)

        if settings.CMIS_ENABLED:
            create_bestandsdeel_kwargs = {"eio_uuid": eio.uuid}
        else:
            # The serialiser .create() method does not support nested data, so these have to be added separately
            eio.integriteit = integriteit
            eio.ondertekening = ondertekening
            eio.save()

            create_bestandsdeel_kwargs = {"canonical": canonical}

            # create empty file if size == 0
            if eio.bestandsomvang == 0:
                eio.inhoud.save("empty_file", ContentFile(""))

        # large file process
        if not eio.inhoud and eio.bestandsomvang and eio.bestandsomvang > 0:
            self._create_bestandsdeel(
                validated_data["bestandsomvang"], **create_bestandsdeel_kwargs
            )

        return eio

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # With Alfresco, the URL cannot be retrieved using the
        # latest_version property of the canonical object
        if settings.CMIS_ENABLED:
            path = reverse(
                "enkelvoudiginformatieobject-detail",
                kwargs={"version": "1", "uuid": instance.uuid},
            )
            # Following what is done in drc_cmis/client/convert.py
            ret["url"] = make_absolute_uri(path, request=self.context.get("request"))
        return ret

    def update(self, instance, validated_data):
        """
        Instead of updating an existing EnkelvoudigInformatieObject,
        create a new EnkelvoudigInformatieObject with the same
        EnkelvoudigInformatieObjectCanonical
        """
        integriteit = (
            validated_data.pop("integriteit", {}) or {}
        )  # integriteit and ondertekening can also be set to None
        ondertekening = validated_data.pop("ondertekening", {}) or {}

        # populate new version with previous version data only for PATCH
        validated_data_field_names = validated_data.keys()
        updatable_field_names = [
            k for k, v in self.get_fields().items() if not v.read_only
        ]
        for field in instance._meta.get_fields():
            if field.name not in validated_data_field_names and (
                self.partial or field.name not in updatable_field_names
            ):
                validated_data[field.name] = getattr(instance, field.name)

        # add vertrouwelijkheidaanduiding
        validated_data["vertrouwelijkheidaanduiding"] = validated_data.get(
            "vertrouwelijkheidaanduiding", instance.vertrouwelijkheidaanduiding
        )
        validated_data["pk"] = None
        validated_data["versie"] += 1

        if settings.CMIS_ENABLED:
            # The fields integriteit and ondertekening are of "GegevensGroepType", so they need to be
            # flattened before sending to the DMS
            flat_integriteit = flatten_gegevens_groep(integriteit, "integriteit")
            flat_ondertekening = flatten_gegevens_groep(ondertekening, "ondertekening")
            validated_data.update(**flat_integriteit, **flat_ondertekening)
        else:
            # Remove the lock from the data from which a new
            # EnkelvoudigInformatieObject will be created, because lock is not a
            # part of that model
            validated_data.pop("lock")

        validated_data["_request"] = self.context.get("request")
        instance = super().create(validated_data)

        if settings.CMIS_ENABLED:
            # each update - delete previous part files
            bestandsdelen = BestandsDeel.objects.filter(
                informatieobject_uuid=instance.uuid
            )
        else:
            # The serialiser .create() method does not support nested data, so these have to be added separately
            instance.integriteit = integriteit
            instance.ondertekening = ondertekening
            instance.save()

            bestandsdelen = instance.canonical.bestandsdelen.all()

        bestandsdelen.wipe()

        if settings.CMIS_ENABLED:
            create_bestandsdeel_kwargs = {"eio_uuid": instance.uuid}
        else:
            create_bestandsdeel_kwargs = {"canonical": instance.canonical}

        # large file process
        if (
            not instance.inhoud
            and instance.bestandsomvang
            and instance.bestandsomvang > 0
        ):
            self._create_bestandsdeel(
                instance.bestandsomvang, **create_bestandsdeel_kwargs
            )

        # create empty file if size == 0
        if (
            not settings.CMIS_ENABLED
            and instance.bestandsomvang == 0
            and not instance.inhoud
        ):
            instance.inhoud.save("empty_file", ContentFile(""))

        return instance


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

        # Removing the validator that checks for identificatie/bronorganisatie being unique together, because for a
        # PATCH request to update a document all the data from the previous document version is used.
        validators = [StatusValidator()]

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

        if lock != self.instance.canonical.lock:
            raise serializers.ValidationError(
                _("Lock id is not correct"), code="incorrect-lock-id"
            )

        return valid_attrs


class EnkelvoudigInformatieObjectCreateLockSerializer(
    EnkelvoudigInformatieObjectSerializer
):
    """
    This serializer class is used by EnkelvoudigInformatieObjectViewSet for
    create operation for large files
    """

    lock = serializers.CharField(
        read_only=True,
        source="canonical.lock",
        help_text=_(
            "Lock id generated if the large file is created and should be used "
            "while updating the document. Documents with base64 encoded files "
            "are created without lock"
        ),
    )

    class Meta(EnkelvoudigInformatieObjectSerializer.Meta):
        # Use the same fields as the parent class and add the lock to it
        fields = EnkelvoudigInformatieObjectSerializer.Meta.fields + ("lock",)
        extra_kwargs = EnkelvoudigInformatieObjectSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update(
            {
                "lock": {
                    "source": "canonical.lock",
                    "read_only": True,
                }
            }
        )

    def create(self, validated_data):
        eio = super().create(validated_data)

        # lock document if it is a large file upload
        if not eio.inhoud and eio.bestandsomvang and eio.bestandsomvang > 0:
            if settings.CMIS_ENABLED:
                eio.canonical.lock_document(eio.uuid)
            else:
                eio.canonical.lock = uuid.uuid4().hex
                eio.canonical.save()
        return eio


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

    @transaction.atomic
    def save(self, **kwargs):
        # The lock method of the EnkelvoudigInformatieObjectViewSet creates a LockEnkelvoudigInformatieObjectSerializer
        # with a context containing the request and the url parameter uuid.
        self.instance.lock_document(doc_uuid=self.context["uuid"])
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
        if lock != self.instance.canonical.lock:
            raise serializers.ValidationError(
                _("Lock id is not correct"), code="incorrect-lock-id"
            )

        if settings.CMIS_ENABLED:
            all_parts = BestandsDeel.objects.filter(
                informatieobject_uuid=self.instance.uuid
            )
        else:
            all_parts = self.instance.canonical.bestandsdelen.all()

        complete_upload = all_parts.complete_upload
        empty_bestandsdelen = all_parts.empty_bestandsdelen

        if not complete_upload and not empty_bestandsdelen:
            raise serializers.ValidationError(
                _("Upload of part files is not complete"), code="incomplete-upload"
            )
        is_empty = empty_bestandsdelen and not self.instance.inhoud
        if is_empty and self.instance.bestandsomvang > 0:
            raise serializers.ValidationError(
                _("Either file should be upload or the file size = 0"), code="file-size"
            )
        return valid_attrs

    def save(self, **kwargs):
        # merge files and clean bestandsdelen

        # Because it is a large file upload, the document is immediately locked after
        # creation. This means that attempting to save the merged inhoud causes CMIS
        # exceptions (because the document is already locked and thus checked out)
        # If we do not force unlocking, CMIS will complain about the bestandsomvang not
        # being the same as the actual file size
        force_unlock = True if settings.CMIS_ENABLED else self.context["force_unlock"]
        self.instance.canonical.unlock_document(
            doc_uuid=self.context["uuid"],
            lock=self.context["request"].data.get("lock"),
            force_unlock=force_unlock,
        )
        self.instance.canonical.save()

        if settings.CMIS_ENABLED:
            bestandsdelen = BestandsDeel.objects.filter(
                informatieobject_uuid=self.instance.uuid
            ).order_by("volgnummer")
        else:
            bestandsdelen = self.instance.canonical.bestandsdelen.order_by("volgnummer")

        complete_upload = bestandsdelen.complete_upload
        empty_bestandsdelen = bestandsdelen.empty_bestandsdelen

        if empty_bestandsdelen:
            return self.instance

        if complete_upload:
            part_files = [p.inhoud.file for p in bestandsdelen]
            # create the name of target file using the storage backend to the serializer
            name = create_filename(self.instance.bestandsnaam)
            file_field = self.instance._meta.get_field("inhoud")
            rel_path = file_field.generate_filename(self.instance, name)
            file_name = Path(rel_path).name
            # merge files
            file_dir = Path(settings.PRIVATE_MEDIA_ROOT)
            target_file = merge_files(part_files, file_dir, file_name)
            # save full file to the instance FileField
            with open(target_file, "rb") as file_obj:
                self.instance.inhoud = File(file_obj, name=file_name)
                self.instance.save()

            # Remove the merged file
            target_file.unlink()
        else:
            self.instance.bestandsomvang = None
            self.instance.save()

        # delete part files
        bestandsdelen.wipe()

        return self.instance


class EIOZoekSerializer(serializers.Serializer):
    uuid__in = serializers.ListField(
        child=serializers.UUIDField(),
        help_text=_("Array of unieke resource identifiers (UUID4)"),
    )


class GebruiksrechtenSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name="enkelvoudiginformatieobject-detail",
        lookup_field="uuid",
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text("documenten.Gebruiksrechten", "informatieobject"),
    )

    inclusion_serializers = {
        "informatieobject": f"{oz}.documenten.api.serializers.EnkelvoudigInformatieObjectSerializer",
        "informatieobject.informatieobjecttype": f"{oz}.catalogi.api.serializers.InformatieObjectTypeSerializer",
    }

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

    def create(self, validated_data):
        if settings.CMIS_ENABLED:
            # The URL of the EnkelvoudigInformatieObject is needed rather than the canonical object
            if validated_data.get("informatieobject") is not None:
                validated_data["informatieobject"] = self.initial_data[
                    "informatieobject"
                ]
        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # With Alfresco, the URL of the Gebruiksrechten and EnkelvoudigInformatieObject
        # cannot be retrieved using the latest_version property of the canonical object
        if settings.CMIS_ENABLED:
            path = reverse(
                "gebruiksrechten-detail", kwargs={"version": 1, "uuid": instance.uuid}
            )
            ret["url"] = make_absolute_uri(path, request=self.context.get("request"))
            ret["informatieobject"] = instance.get_informatieobject_url()
        return ret


class ObjectInformatieObjectSerializer(serializers.HyperlinkedModelSerializer):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name="enkelvoudiginformatieobject-detail",
        lookup_field="uuid",
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text(
            "documenten.ObjectInformatieObject", "informatieobject"
        ),
    )
    object = OnlyRemoteOrFKOrURLField(
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

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(ObjectInformatieObjectTypes)
        fields["object_type"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def set_object_properties(self, object_type: str) -> None:
        object_field = self.fields["object"]

        if object_type == ObjectInformatieObjectTypes.besluit:
            object_field.source = "besluit"
            object_field.validators.append(
                LooseFkResourceValidator("Besluit", settings.BRC_API_STANDARD)
            )
        elif object_type == ObjectInformatieObjectTypes.zaak:
            object_field.source = "zaak"
            object_field.validators.append(
                LooseFkResourceValidator("Zaak", settings.ZRC_API_STANDARD)
            )
        elif object_type == ObjectInformatieObjectTypes.verzoek:
            object_field.source = "verzoek"
            object_field.validators.append(verzoek_validator)

    def to_internal_value(self, data):
        object_type = data["object_type"]
        # validate that it's a valid object type first
        try:
            self.fields["object_type"].run_validation(object_type)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"object_type": exc.detail})

        self.set_object_properties(object_type)
        res = super().to_internal_value(data)
        if settings.CMIS_ENABLED:
            # res contains the canonical object instead of the document url, but if only the
            # canonical object is given, the document cannot be retrieved from Alfresco
            res["informatieobject"] = data["informatieobject"]
        return res

    def to_representation(self, instance):
        object_type = instance.object_type
        self.set_object_properties(object_type)
        ret = super().to_representation(instance)
        if settings.CMIS_ENABLED:
            # Objects without a primary key will have 'None' as the URL, so it is added manually
            path = reverse(
                "objectinformatieobject-detail",
                kwargs={"version": 1, "uuid": instance.uuid},
            )
            ret["url"] = make_absolute_uri(path, request=self.context.get("request"))
            ret["informatieobject"] = instance.get_informatieobject_url()

        return ret

    def create(self, validated_data):
        object_type = validated_data["object_type"]
        validated_data[object_type] = validated_data.pop("object")

        oio = super().create(validated_data)
        return oio


# Verzending
class BinnenlandsCorrespondentieadresVerzendingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Verzending
        gegevensgroep = "binnenlands_correspondentieadres"


class BuitenlandsCorrespondentieadresVerzendingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Verzending
        gegevensgroep = "buitenlands_correspondentieadres"


class CorrespondentiePostadresVerzendingSerializer(GegevensGroepSerializer):
    class Meta:
        model = Verzending
        gegevensgroep = "correspondentie_postadres"


class VerzendingSerializer(
    NestedGegevensGroepMixin,
    serializers.HyperlinkedModelSerializer,
):
    informatieobject = EnkelvoudigInformatieObjectHyperlinkedRelatedField(
        view_name="enkelvoudiginformatieobject-detail",
        lookup_field="uuid",
        queryset=EnkelvoudigInformatieObject.objects,
        help_text=get_help_text("documenten.Verzending", "informatieobject"),
    )

    binnenlands_correspondentieadres = (
        BinnenlandsCorrespondentieadresVerzendingSerializer(
            required=False,
            allow_null=True,
            help_text=_(
                "Het correspondentieadres, betreffende een adresseerbaar object,"
                " van de BETROKKENE, zijnde afzender of geadresseerde, zoals vermeld"
                " in het ontvangen of verzonden INFORMATIEOBJECT indien dat afwijkt"
                " van het reguliere binnenlandse correspondentieadres van BETROKKENE."
            ),
        )
    )

    buitenlands_correspondentieadres = (
        BuitenlandsCorrespondentieadresVerzendingSerializer(
            required=False,
            allow_null=True,
            help_text=_(
                "De gegevens van het adres in het buitenland van BETROKKENE, zijnde"
                " afzender of geadresseerde, zoals vermeld in het ontvangen of"
                " verzonden INFORMATIEOBJECT en dat afwijkt van de reguliere"
                " correspondentiegegevens van BETROKKENE."
            ),
        )
    )

    correspondentie_postadres = CorrespondentiePostadresVerzendingSerializer(
        required=False,
        allow_null=True,
        help_text=_(
            "De gegevens die tezamen een postbusadres of antwoordnummeradres"
            " vormen van BETROKKENE, zijnde afzender of geadresseerde, zoals"
            " vermeld in het ontvangen of verzonden INFORMATIEOBJECT en dat"
            " afwijkt van de reguliere correspondentiegegevens van BETROKKENE."
        ),
    )

    inclusion_serializers = {
        "informatieobject": f"{oz}.documenten.api.serializers.EnkelvoudigInformatieObjectSerializer",
        "informatieobject.informatieobjecttype": f"{oz}.catalogi.api.serializers.InformatieObjectTypeSerializer",
    }

    class Meta:
        model = Verzending
        fields = (
            "url",
            "betrokkene",
            "informatieobject",
            "aard_relatie",
            "toelichting",
            "ontvangstdatum",
            "verzenddatum",
            "contact_persoon",
            "contactpersoonnaam",
            "binnenlands_correspondentieadres",
            "buitenlands_correspondentieadres",
            "correspondentie_postadres",
            "faxnummer",
            "emailadres",
            "mijn_overheid",
            "telefoonnummer",
        )

        extra_kwargs = {
            "url": {"lookup_field": "uuid", "read_only": True},
        }
        validators = [VerzendingAddressValidator()]
