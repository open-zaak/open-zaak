from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject


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

        if not besluittype.zaaktypen.filter(uuid=zaak.zaaktype.uuid).exists():
            raise serializers.ValidationError(self.message, code=self.code)


class BesluittypeInformatieobjecttypeRelationValidator:
    code = "missing-besluittype-informatieobjecttype-relation"
    message = _(
        "Het informatieobjecttype hoort niet bij het besluitype van de besluit."
    )

    def __call__(self, attrs):
        informatieobject = attrs.get("informatieobject")
        besluit = attrs.get("besluit")

        if not isinstance(informatieobject, EnkelvoudigInformatieObject):
            io_type = informatieobject.latest_version.informatieobjecttype
        else:
            io_type = informatieobject.informatieobjecttype

        if not besluit.besluittype.informatieobjecttypen.filter(uuid=io_type.uuid).exists():
            raise serializers.ValidationError(self.message, code=self.code)
