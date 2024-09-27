# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from vng_api_common.serializers import add_choice_values_help_text
from vng_api_common.validators import validate_rsin as validate_bsn


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
class DigiDLevelOfAssurance(models.TextChoices):
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
class eHerkenningLevelOfAssurance(models.TextChoices):
    non_existent = "urn:etoegang:core:assurance-class:loa1", _("Non existent (1)")
    low = "urn:etoegang:core:assurance-class:loa2", _("Low (2)")
    low_plus = "urn:etoegang:core:assurance-class:loa2plus", _("Low (2+)")
    substantial = "urn:etoegang:core:assurance-class:loa3", _("Substantial (3)")
    high = "urn:etoegang:core:assurance-class:loa4", _("High (4)")


class DigiDRepresentee(serializers.Serializer):
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


class DigiDMandateServiceSerializer(serializers.Serializer):
    id = serializers.CharField(label=_("service ID"))


class DigiDMandate(serializers.Serializer):
    services = DigiDMandateServiceSerializer(many=True)


class DigiDAuthContextSerializer(serializers.Serializer):
    source = serializers.ChoiceField(
        required=True,
        label=_("Source"),
        choices=((AuthSource.digid.value, AuthSource.digid.label),),
        help_text=_("DigiD is the only way a Natural Person can be identified."),
    )
    level_of_assurance = serializers.ChoiceField(
        required=False,
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
    representee = DigiDRepresentee(
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
    mandate = DigiDMandate(
        label=_("mandate context"),
        required=False,
        help_text=_(
            "The mandate (\"machtiging') describes the extent of the mandate granted "
            "from the representee to the authorizee. For DigiD, the mandate is tied "
            "to a a service or a set of services. Each service is identified by an "
            "ID, passed along by Logius in the authentication flow.\n\n"
            "The `mandate` key is required if a `representee` is specified."
        ),
    )

    def get_fields(self):
        fields = super().get_fields()

        value_display_mapping = add_choice_values_help_text(DigiDLevelOfAssurance)
        fields["level_of_assurance"].help_text += f"\n\n{value_display_mapping}"

        return fields

    def validate(self, attrs):
        if attrs.get("representee") and not attrs.get("mandate"):
            error = ErrorDetail(
                _("The mandate context is required when a representee is specified."),
                code="required",
            )
            raise serializers.ValidationError({"mandate": error})

        return attrs
