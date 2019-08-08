from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.models import APICredential
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator
)


def fetch_object(resource: str, url: str) -> dict:
    Client = import_string(settings.ZDS_CLIENT_CLASS)
    client = Client.from_url(url)
    client.auth = APICredential.get_auth(url)
    obj = client.retrieve(resource, url=url)
    return obj


class RolOccurenceValidator:
    """
    Validate that max x occurences of a field occur for a related object.

    Should be applied to the serializer class, not to an individual field
    """
    message = _('There are already {num} `{value}` occurences')

    def __init__(self, omschrijving_generiek: str, max_amount: int=1):
        self.omschrijving_generiek = omschrijving_generiek
        self.max_amount = max_amount

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, 'instance', None)

    def __call__(self, attrs):
        roltype = fetch_object("roltype", attrs["roltype"])

        attrs["omschrijving"] = roltype["omschrijving"]
        attrs["omschrijving_generiek"] = roltype["omschrijvingGeneriek"]

        if attrs['omschrijving_generiek'] != self.omschrijving_generiek:
            return

        is_noop_update = self.instance and self.instance.omschrijving_generiek == self.omschrijving_generiek
        if is_noop_update:
            return

        existing = (
            attrs['zaak']
            .rol_set
            .filter(omschrijving_generiek=self.omschrijving_generiek)
            .count()
        )

        if existing >= self.max_amount:
            message = self.message.format(num=existing, value=self.omschrijving_generiek)
            raise serializers.ValidationError({
                'roltype': message
            }, code='max-occurences')


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van bronorganisatie en zaak uniek is.
    """
    message = _('Deze identificatie bestaat al voor deze bronorganisatie')

    def __init__(self):
        super().__init__('bronorganisatie', 'identificatie')


class NotSelfValidator:
    code = 'self-forbidden'
    message = _("The '{field_name}' may not be a self-reference")

    def set_context(self, field):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.field_name = field.field_name
        self.instance = getattr(field.root, 'instance', None)

    def __call__(self, obj: models.Model):
        if self.instance == obj:
            message = self.message.format(field_name=self.field_name)
            raise serializers.ValidationError(message, code=self.code)


class HoofdzaakValidator:
    code = 'deelzaak-als-hoofdzaak'
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

        obj = fetch_object(self.resource, url)
        if obj["zaaktype"] != zaak.zaaktype:
            raise serializers.ValidationError(self.message, code=self.code)


class ZaaktypeInformatieobjecttypeRelationValidator:
    code = "missing-zaaktype-informatieobjecttype-relation"
    message = _("Het informatieobjecttype hoort niet bij het zaaktype van de zaak.")

    def __init__(self, url_field: str, zaak_field: str = "zaak", resource: str = None):
        self.url_field = url_field
        self.zaak_field = zaak_field
        self.resource = resource or url_field

    def __call__(self, attrs):
        url = attrs.get(self.url_field)
        zaak = attrs.get(self.zaak_field)
        if not url or not zaak:
            return

        obj = fetch_object(self.resource, url)
        zaaktype = fetch_object('zaaktype', zaak.zaaktype)

        if obj['informatieobjecttype'] not in zaaktype['informatieobjecttypen']:
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
