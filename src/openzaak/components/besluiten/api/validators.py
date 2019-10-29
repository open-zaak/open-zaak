from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van verantwoordelijke organisatie en
    identificatie uniek is.
    """

    message = _("Deze identificatie bestaat al voor deze verantwoordelijke organisatie")

    def __init__(self):
        super().__init__("verantwoordelijke_organisatie", "identificatie")


class BesluittypeZaaktypeValidator:
    code = "zaaktype-mismatch"
    message = _("De referentie hoort niet bij het zaaktype van de zaak.")

    def __call__(self, attrs):
        besluittype = attrs.get("besluittype")
        zaak = attrs.get("zaak")

        if not zaak:
            return

        if not besluittype.zaaktypes.filter(
            id=zaak.zaaktype_id, concept=False
        ).exists():
            raise serializers.ValidationError(self.message, code=self.code)


class ZaaktypeInformatieobjecttypeRelationValidator:
    code = "missing-zaaktype-informatieobjecttype-relation"
    message = _("Het informatieobjecttype hoort niet bij het zaaktype van de zaak.")

    def __call__(self, attrs):
        informatieobject = attrs.get("informatieobject")
        besluit = attrs.get("besluit")

        io = informatieobject.enkelvoudiginformatieobject_set.first()
        if not besluit.besluittype.informatieobjecttypen.filter(
            id=io.informatieobjecttype_id, concept=False
        ).exists():
            raise serializers.ValidationError(self.message, code=self.code)
