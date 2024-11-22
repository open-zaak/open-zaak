# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import validate_rsin as validate_bsn

from openzaak.utils.choices import OrderedTextChoices

from ..validators import AuthContextMandateValidator


class AuthSource(models.TextChoices):
    # Reference enum on:
    # https://github.com/maykinmedia/authentication-context-schemas/blob/
    #   3df9b845c3856d657c8b9d3849a8364c505bd91c/schemas/base.json#L13
    #
    # Only DigiD/eHerkenning are within scope for the experiment/first iteration, eIDAS
    # and custom can be supported in the future.
    digid = "digid", _("DigiD")
    eherkenning = "eherkenning", _("eHerkenning")


# Taken from django-digid-eherkenning: ``digid_eherkenning.choices``
class DigiDLevelOfAssurance(OrderedTextChoices):
    base = (
        "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
        _("DigiD Basis"),
    )
    middle = (
        "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract",
        _("DigiD Midden"),
    )
    substantial = (
        "urn:oasis:names:tc:SAML:2.0:ac:classes:Smartcard",
        _("DigiD Substantieel"),
    )
    high = (
        "urn:oasis:names:tc:SAML:2.0:ac:classes:SmartcardPKI",
        _("DigiD Hoog"),
    )


# Taken from django-digid-eherkenning: ``digid_eherkenning.choices``
class eHerkenningLevelOfAssurance(OrderedTextChoices):
    non_existent = "urn:etoegang:core:assurance-class:loa1", _("Non existent (1)")
    low = "urn:etoegang:core:assurance-class:loa2", _("Low (2)")
    low_plus = "urn:etoegang:core:assurance-class:loa2plus", _("Low (2+)")
    substantial = "urn:etoegang:core:assurance-class:loa3", _("Substantial (3)")
    high = "urn:etoegang:core:assurance-class:loa4", _("High (4)")


# According to https://afsprakenstelsel.etoegang.nl/Startpagina/v2/entityconcernedid-rsin
# RSIN is not allowed for Intermediair
class eHerkenningRepresenteeIdentifier(models.TextChoices):
    bsn = "bsn", _("BSN")
    kvk_nummer = "kvkNummer", _("KVK-nummer")


class eHerkenningMandateRole(models.TextChoices):
    bewindvoerder = "bewindvoerder", "Bewindvoerder"
    curator = "curator", "Curator"
    mentor = "mentor", "Mentor"


class DigiDRepresenteeSerializer(serializers.Serializer):
    identifier_type = serializers.ChoiceField(
        label=_("Identifier type"),
        required=True,
        choices=(("bsn", _("BSN")),),
        help_text=_(
            "Determines how to interpret the `identifier` value. DigiD and DigiD "
            "Machtigen only support BSNs."
        ),
    )
    identifier = serializers.CharField(
        label=_("Identifier"),
        required=True,
        help_text=_(
            "BSN of the person being represented. BSNs must satisfy the 11-proef."
        ),
        min_length=9,
        max_length=9,
        validators=[validate_bsn],
    )


class eHerkenningRepresenteeSerializer(serializers.Serializer):
    identifier_type = serializers.ChoiceField(
        label=_("Identifier type"),
        required=True,
        choices=eHerkenningRepresenteeIdentifier.choices,
        help_text=_(
            "Determines how to interpret the `identifier` value. EHerkenning "
            "only supports BSN and KVK-nummer."
        ),
    )
    identifier = serializers.CharField(
        label=_("Identifier"),
        required=True,
        help_text=_("Identifier of the represented person or the company"),
        max_length=9,
    )

    def validate(self, attrs):
        valid_attrs = super().validate(attrs)

        identifier_type = valid_attrs["identifier_type"]
        identifier = valid_attrs["identifier"]
        if identifier_type == eHerkenningRepresenteeIdentifier.bsn:
            validate_bsn(identifier)
        elif identifier_type == eHerkenningRepresenteeIdentifier.kvk_nummer:
            # KVK-nummer has only 8 chars
            MaxLengthValidator(limit_value=8)(identifier)

        return valid_attrs


class DigiDMandateServiceSerializer(serializers.Serializer):
    id = serializers.CharField(label=_("service ID"))


class DigiDMandateSerializer(serializers.Serializer):
    services = DigiDMandateServiceSerializer(many=True)


class eHerkenningServiceSerializer(serializers.Serializer):
    id = serializers.CharField(
        label=_("Service ID"), help_text=_("The ServiceID from the service catalog")
    )
    uuid = serializers.UUIDField(
        label=_("Service UUID"), help_text=_("The ServiceUUID from the service catalog")
    )


class eHerkenningMandateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        required=False,
        label=_("Role"),
        choices=eHerkenningMandateRole.choices,
        help_text=_(
            "The role of a mandate, typically assigned through judicial procedures"
        ),
    )
    services = eHerkenningServiceSerializer(many=True)


class DigiDAuthContextSerializer(serializers.Serializer):
    source = serializers.ChoiceField(
        required=True,
        label=_("Source"),
        choices=((AuthSource.digid.value, AuthSource.digid.label),),
        help_text=_("DigiD is the only way a Natural Person can be identified."),
    )
    level_of_assurance = serializers.ChoiceField(
        required=True,
        label=_("Level of assurance"),
        choices=DigiDLevelOfAssurance.choices,
        help_text=_(
            "Indicates how strong the identity claim is. Logius defines the available "
            "levels of assurance *and* prescribes what the minimum level must be. "
            "Recording this context allows portals to only display cases with a lower "
            "or equal level of assurance in the currently active portal authentication "
            "context."
        ),
    )
    representee = DigiDRepresenteeSerializer(
        label=_("represented person"),
        required=False,
        help_text=_(
            "When registering the role for the authorizee, you should include the "
            "representee to make clear a mandate applies. This also requires you to "
            "specify the `mandate` key and its context. If you provide a representee, "
            "You should also create an additional `rol` with `rolomschrijvingGeneriek` "
            "equal to `belanghebbende`, and set `indicatieMachtiging` to "
            "`machtiginggever`."
        ),
    )
    mandate = DigiDMandateSerializer(
        label=_("mandate context"),
        required=False,
        help_text=_(
            "The mandate (\"machtiging') describes the extent of the mandate granted "
            "from the representee to the authorizee. For DigiD, the mandate is tied "
            "to a service or a set of services. Each service is identified by an "
            "ID, passed along by Logius in the authentication flow.\n\n"
            "The `mandate` key is required if a `representee` is specified."
        ),
    )

    class Meta:
        validators = [AuthContextMandateValidator()]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(DigiDLevelOfAssurance)
        fields["level_of_assurance"].help_text += f"\n\n{value_display_mapping}"

        return fields


class eHerkenningAuthContextSerializer(serializers.Serializer):
    source = serializers.ChoiceField(
        required=True,
        label=_("Source"),
        choices=((AuthSource.eherkenning.value, AuthSource.eherkenning.label),),
        help_text=_(
            "eHerkenning is the only way a Non-Natural Person or the Branch of a company "
            "can be identified."
        ),
    )
    level_of_assurance = serializers.ChoiceField(
        required=True,
        label=_("Level of assurance"),
        choices=eHerkenningLevelOfAssurance.choices,
        help_text=_(
            "Indicates how strong the identity claim is. Elektronische Toegangsdiensten "
            "defines the available levels of assurance. Recording this context allows "
            "portals to only display cases with a lower or equal level of assurance "
            "in the currently active portal authentication context."
        ),
    )
    # Specification by eHerkenning - https://afsprakenstelsel.etoegang.nl/Startpagina/v3/specific-pseudonym
    acting_subject = serializers.CharField(
        required=True,
        max_length=100,
        help_text=_(
            "The identifier is always some encrypted form, specific to the service provider. "
            "I.e. the same physical person gets different identifier values when authenticating "
            "with different service providers. Unencrypted details of the acting subject can be "
            "added to the `contactpersoonRol.naam` attribute"
        ),
    )
    representee = eHerkenningRepresenteeSerializer(
        label=_("represented party"),
        required=False,
        help_text=_(
            "When registering the role for the authorizee, you should include the "
            "representee to make clear a mandate applies. This also requires you to "
            "specify the `mandate` key and its context. If you provide a representee, "
            "You should also create an additional `rol` with `rolomschrijvingGeneriek` "
            "equal to `belanghebbende`, and set `indicatieMachtiging` to "
            "`machtiginggever`."
        ),
    )
    mandate = eHerkenningMandateSerializer(
        label=_("mandate context"),
        required=False,
        help_text=_(
            "The mandate ('machtiging') describes the extent of the mandate granted "
            "from the representee to the authorizee. "
            "The `mandate` key is required if a `representee` is specified."
        ),
    )

    class Meta:
        validators = [AuthContextMandateValidator()]

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(eHerkenningLevelOfAssurance)
        fields["level_of_assurance"].help_text += f"\n\n{value_display_mapping}"

        return fields
