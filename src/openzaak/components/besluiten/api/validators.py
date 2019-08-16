from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator
)


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

    def __call__(self, attrs):
        besluittype = attrs.get('besluittype')
        zaak = attrs.get('zaak')

        if not zaak:
            return

        if zaak.zaaktype not in besluittype.zaaktypes.all():
            raise serializers.ValidationError(self.message, code=self.code)


class ZaaktypeInformatieobjecttypeRelationValidator:
    code = "missing-zaaktype-informatieobjecttype-relation"
    message = _("Het informatieobjecttype hoort niet bij het zaaktype van de zaak.")

    def __call__(self, attrs):
        informatieobject = attrs.get('informatieobject')
        besluit = attrs.get('besluit')

        if not besluit.zaak:
            return

        io_informatieobjecttype = informatieobject.latest_version.informatieobjecttype
        besluit_informatieobjecttypes = besluit.zaak.zaaktype.heeft_relevant_informatieobjecttype.all()
        if io_informatieobjecttype not in besluit_informatieobjecttypes:
            raise serializers.ValidationError(self.message, code=self.code)
