from django.conf import settings
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


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van verantwoordelijke organisatie en
    identificatie uniek is.
    """
    message = _('Deze identificatie bestaat al voor deze verantwoordelijke organisatie')

    def __init__(self):
        super().__init__('verantwoordelijke_organisatie', 'identificatie')


class BesluittypeZaaktypeValidator:
    code = "zaaktype-mismatch"
    message = _("De referentie hoort niet bij het zaaktype van de zaak.")

    def __init__(self, url_field: str, zaak_field: str = "zaak", resource: str = None):
        self.url_field = url_field
        self.zaak_field = zaak_field
        self.resource = resource or url_field

    def __call__(self, attrs):
        url = attrs.get(self.url_field)
        zaak_url = attrs.get(self.zaak_field)
        if not url or not zaak_url:
            return

        besluittype = fetch_object(self.resource, url)
        zaak = fetch_object(self.zaak_field, zaak_url)
        if zaak['zaaktype'] not in besluittype['zaaktypes']:
            raise serializers.ValidationError(self.message, code=self.code)


class ZaaktypeInformatieobjecttypeRelationValidator:
    code = "missing-zaaktype-informatieobjecttype-relation"
    message = _("Het informatieobjecttype hoort niet bij het zaaktype van de zaak.")

    def __init__(self, url_field: str, besluit_field: str = "besluit", resource: str = None):
        self.url_field = url_field
        self.besluit_field = besluit_field
        self.resource = resource or url_field

    def __call__(self, attrs):
        informatieobject_url = attrs.get(self.url_field)
        besluit = attrs.get(self.besluit_field)
        if not informatieobject_url or not besluit:
            return

        # Only apply validation if the Besluit is linked to a Zaak
        if besluit.zaak:
            zaak = fetch_object('zaak', besluit.zaak)
            zaaktype = fetch_object('zaaktype', zaak['zaaktype'])
            informatieobject = fetch_object(self.resource, informatieobject_url)
            if informatieobject['informatieobjecttype'] not in zaaktype['informatieobjecttypen']:
                raise serializers.ValidationError(self.message, code=self.code)
