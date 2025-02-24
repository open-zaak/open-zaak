# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
            raise ValidationError(self.message, code=self.code)
