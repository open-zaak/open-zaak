# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)

from openzaak.loaders import AuthorizedRequestsLoader


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

    def set_context(self, serializer):
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs):
        besluittype = attrs.get("besluittype") or self.instance.besluittype
        zaak = attrs.get("zaak") or getattr(self.instance, "zaak", None)

        if not zaak:
            return

        zaaktype = zaak.zaaktype

        if bool(zaaktype.pk) != bool(besluittype.pk):
            msg_diff = _(
                "Het besluittype en het zaaktype van de zaak moeten tot dezelfde catalogus behoren."
            )
            raise serializers.ValidationError(msg_diff, code=self.code)

        # local zaaktype/besluittype
        if besluittype.pk:
            if not besluittype.zaaktypen.filter(uuid=zaaktype.uuid).exists():
                raise serializers.ValidationError(self.message, code=self.code)

        # external zaaktype/besluittype - workaround since loose-fk field doesn't support m2m relations
        else:
            besluittype_url = besluittype._loose_fk_data["url"]
            zaaktype_url = zaaktype._loose_fk_data["url"]
            besluittype_data = AuthorizedRequestsLoader.fetch_object(
                besluittype_url, do_underscoreize=False
            )
            if zaaktype_url not in besluittype_data.get("zaaktypen", []):
                raise serializers.ValidationError(self.message, code=self.code)
