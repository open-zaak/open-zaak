# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Max, Subquery
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.constants import Archiefstatus
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)

from openzaak.components.documenten.constants import Statussen
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)

from ..models import Zaak


class RolOccurenceValidator:
    """
    Validate that max x occurences of a field occur for a related object.

    Should be applied to the serializer class, not to an individual field
    """

    message = _("There are already {num} `{value}` occurences")

    def __init__(self, omschrijving_generiek: str, max_amount: int = 1):
        self.omschrijving_generiek = omschrijving_generiek
        self.max_amount = max_amount

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs):
        roltype = attrs["roltype"]

        attrs["omschrijving"] = roltype.omschrijving
        attrs["omschrijving_generiek"] = roltype.omschrijving_generiek

        if attrs["omschrijving_generiek"] != self.omschrijving_generiek:
            return

        is_noop_update = (
            self.instance
            and self.instance.omschrijving_generiek == self.omschrijving_generiek
        )
        if is_noop_update:
            return

        existing = (
            attrs["zaak"]
            .rol_set.filter(omschrijving_generiek=self.omschrijving_generiek)
            .count()
        )

        if existing >= self.max_amount:
            message = self.message.format(
                num=existing, value=self.omschrijving_generiek
            )
            raise serializers.ValidationError(
                {"roltype": message}, code="max-occurences"
            )


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van bronorganisatie en zaak uniek is.
    """

    message = _("Deze identificatie bestaat al voor deze bronorganisatie")

    def __init__(self):
        super().__init__("bronorganisatie", "identificatie")


class NotSelfValidator:
    code = "self-forbidden"
    message = _("The '{field_name}' may not be a self-reference")

    def set_context(self, field):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.field_name = field.field_name
        self.instance = getattr(field.root, "instance", None)

    def __call__(self, obj: models.Model):
        if self.instance == obj:
            message = self.message.format(field_name=self.field_name)
            raise serializers.ValidationError(message, code=self.code)


class HoofdzaakValidator:
    code = "deelzaak-als-hoofdzaak"
    message = _("Deelzaken van deelzaken wordt niet ondersteund.")

    def __call__(self, obj: models.Model):
        if obj.hoofdzaak_id is not None:
            raise serializers.ValidationError(self.message, code=self.code)


class CorrectZaaktypeValidator:
    code = "zaaktype-mismatch"
    message = _("De referentie hoort niet bij het zaaktype van de zaak.")

    def __init__(self, url_field: str, zaak_field: str = "zaak", resource: str = None):
        self.url_field = url_field
        self.zaak_field = zaak_field
        self.resource = resource or url_field

    def __call__(self, attrs):
        url = attrs.get(self.url_field)
        zaak = attrs.get(self.zaak_field)
        if not url or not zaak:
            return

        if url.zaaktype != zaak.zaaktype:
            raise serializers.ValidationError(self.message, code=self.code)


class DateNotInFutureValidator:
    code = "date-in-future"
    message = _("Deze datum mag niet in de toekomst zijn")

    def __call__(self, value):
        now = timezone.now()
        if type(value) == date:
            now = now.date()

        if value > now:
            raise serializers.ValidationError(self.message, code=self.code)


class ZaakArchiveIOsArchivedValidator:
    """
    On archival of a zaak, validate that the related documents are archived.
    """

    def set_context(self, serializer: serializers.Serializer):
        self.instance = serializer.instance

    def __call__(self, attrs: dict):
        default_archiefstatus = (
            self.instance.archiefstatus
            if self.instance
            else Archiefstatus.nog_te_archiveren
        )
        archiefstatus = attrs.get("archiefstatus", default_archiefstatus)

        # no archiving status set -> nothing to do
        if archiefstatus == Archiefstatus.nog_te_archiveren:
            return

        documents_not_archived_error = serializers.ValidationError(
            {
                "archiefstatus",
                _(
                    "Er zijn gerelateerde informatieobjecten waarvan de `status` nog niet gelijk is aan "
                    "`gearchiveerd`. Dit is een voorwaarde voor het zetten van de `archiefstatus` "
                    "op een andere waarde dan `nog_te_archiveren`."
                ),
            },
            code="documents-not-archived",
        )

        if not settings.CMIS_ENABLED:
            self.validate_local_eios_archived(attrs, documents_not_archived_error)
        self.validate_remote_eios_archived(attrs, documents_not_archived_error)
        self.validate_extra_attributes(attrs)

    def validate_local_eios_archived(
        self, attrs: dict, error: serializers.ValidationError
    ):
        # TODO: check remote ZIO.informatieobject
        # search for related informatieobjects with status != 'gearchiveerd'
        canonical_ids = self.instance.zaakinformatieobject_set.values(
            "_informatieobject_id"
        )
        io_ids = (
            EnkelvoudigInformatieObjectCanonical.objects.filter(
                id__in=Subquery(canonical_ids)
            )
            .annotate(last=Max("enkelvoudiginformatieobject"))
            .values("last")
        )

        if (
            EnkelvoudigInformatieObject.objects.filter(id__in=Subquery(io_ids))
            .exclude(status=Statussen.gearchiveerd)
            .exists()
        ):
            raise error

    def validate_remote_eios_archived(
        self, attrs: dict, error: serializers.ValidationError
    ):
        remote_zios = self.instance.zaakinformatieobject_set.exclude(
            _informatieobject_url=""
        )
        # This is a very naive approach to load all the remote objects - it happens
        # sequentially, while futures.concurrent _could_ be used. Let's see first
        # how performance is in this setup. Because we're looping and exiting as
        # soon as an error condition is found, we can reduce unnecessary network
        # calls.
        for zio in remote_zios:
            if zio.informatieobject.status != Statussen.gearchiveerd:
                raise error

    def validate_extra_attributes(self, attrs: dict):
        for attr in ["archiefnominatie", "archiefactiedatum"]:
            if not attrs.get(
                attr, getattr(self.instance, attr) if self.instance else None
            ):
                raise serializers.ValidationError(
                    {
                        attr: _(
                            "Moet van een waarde voorzien zijn als de 'Archiefstatus' een waarde heeft anders dan "
                            f"'{Archiefstatus.nog_te_archiveren}'."
                        )
                    },
                    code=f"{attr}-not-set",
                )


class EndStatusIOsUnlockedValidator:
    """
    Validate that related InformatieObjects are unlocked when the end status is
    being set.

    The serializer sets the __is_eindstatus attribute in the data dict as
    part of the ``to_internal_value`` method.
    """

    code = "informatieobject-locked"
    message = (
        "Er zijn gerelateerde informatieobjecten die nog gelocked zijn."
        "Deze informatieobjecten moet eerst unlocked worden voordat de zaak afgesloten kan worden."
    )

    def __call__(self, attrs: dict):
        if not attrs.get("__is_eindstatus"):
            return

        zaak = attrs.get("zaak")
        # earlier validation failed possibly
        if not zaak:
            return

        local_zios = zaak.zaakinformatieobject_set.filter(
            _informatieobject__isnull=False,
        )
        if local_zios.exclude(_informatieobject__lock="").exists():
            raise serializers.ValidationError(self.message, code=self.code)

        remote_zios = zaak.zaakinformatieobject_set.exclude(_informatieobject_url="")
        for zio in remote_zios:
            if zio.informatieobject.locked:
                raise serializers.ValidationError(self.message, code=self.code)


class EndStatusIOsIndicatieGebruiksrechtValidator:
    """
    Validate that related InformatieObjects have ``indicatieGebruiksrecht`` set
    when the end status is being set.

    The serializer sets the __is_eindstatus attribute in the data dict as
    part of the ``to_internal_value`` method.
    """

    code = "indicatiegebruiksrecht-unset"
    message = (
        "Er zijn gerelateerde informatieobjecten waarvoor `indicatieGebruiksrecht` nog niet "
        "gespecifieerd is. Je moet deze zetten voor je de zaak kan afsluiten."
    )

    def __call__(self, attrs: dict):
        if not attrs.get("__is_eindstatus"):
            return

        zaak = attrs.get("zaak")
        # earlier validation failed possibly
        if not zaak:
            return

        if not settings.CMIS_ENABLED:
            self.validate_local_eios_indicatie_set(zaak)
        self.validate_remote_eios_indicatie_set(zaak)

    def validate_local_eios_indicatie_set(self, zaak: Zaak):
        canonical_ids = zaak.zaakinformatieobject_set.values("_informatieobject_id")
        io_ids = (
            EnkelvoudigInformatieObjectCanonical.objects.filter(
                id__in=Subquery(canonical_ids)
            )
            .annotate(last=Max("enkelvoudiginformatieobject"))
            .values("last")
        )

        if (
            EnkelvoudigInformatieObject.objects.filter(id__in=Subquery(io_ids))
            .filter(indicatie_gebruiksrecht__isnull=True)
            .exists()
        ):
            raise serializers.ValidationError(self.message, self.code)

    def validate_remote_eios_indicatie_set(self, zaak: Zaak):
        remote_zios = zaak.zaakinformatieobject_set.exclude(_informatieobject_url="")
        for zio in remote_zios:
            if zio.informatieobject.indicatie_gebruiksrecht is None:
                raise serializers.ValidationError(self.message, self.code)
