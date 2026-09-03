# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from vng_api_common.validators import (
    UniekeIdentificatieValidator as _UniekeIdentificatieValidator,
)


class UniekeIdentificatieValidator(_UniekeIdentificatieValidator):
    """
    Valideer dat de combinatie van verantwoordelijke organisatie en
    identificatie uniek is.
    """

    message = _(
        "Deze identificatie ({identificatie}) bestaat al voor deze verantwoordelijke organisatie"
    )

    def __init__(self):
        super().__init__("verantwoordelijke_organisatie", "identificatie")


class BesluittypeZaaktypeValidator:
    code = "zaaktype-mismatch"
    message = _("De referentie hoort niet bij het zaaktype van de zaak.")
    requires_context = True

    def __call__(self, attrs, serializer):
        instance = getattr(serializer, "instance", None)
        besluittype = attrs.get("besluittype") or instance.besluittype
        zaak = attrs.get("zaak") or getattr(instance, "zaak", None)

        if not zaak:
            return

        zaaktype = zaak.zaaktype

        if not besluittype.zaaktypen.filter(uuid=zaaktype.uuid).exists():
            raise serializers.ValidationError(self.message, code=self.code)
