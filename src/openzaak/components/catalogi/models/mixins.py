# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _


class GeldigheidMixin(models.Model):
    datum_begin_geldigheid = models.DateField(
        _("datum begin geldigheid"), help_text=_("De datum waarop het is ontstaan.")
    )
    datum_einde_geldigheid = models.DateField(
        _("datum einde geldigheid"),
        blank=True,
        null=True,
        help_text=_("De datum waarop het is opgeheven."),
    )

    class Meta:
        abstract = True

    def clean(self):
        """
        Validate the rule
        De datum is gelijk aan of gelegen na de datum zoals opgenomen onder 'Datum begin geldigheid’.

        This rule applies to the following models,
        # TODO: call the super() in the clean of all those models.
        # TODO: add the other rules for begin_ and einde_geldigheid

        - Besluittype
            - begin: De datum is gelijk aan een Versiedatum van een gerelateerd zaaktype.
            - eind: De datum is gelijk aan de dag voor een Versiedatum van een gerelateerd zaaktype.

        - ZaakType
            CHECK
            - begin De datum is gelijk aan de vroegste Versiedatum van het zaaktype.
            - eind  GEEN CHECK voor gerelateerd zaaktype
            EXTRA: veld 'versie datum'
            De Versiedatum is gelijk aan of ligt na de Datum begin geldigheid zaaktype
            en is gelijk aan of ligt voor de Datum einde geldigheid zaaktype

        """
        super().clean()

        if self.datum_einde_geldigheid:
            if self.datum_einde_geldigheid < self.datum_begin_geldigheid:
                raise ValidationError(
                    _(
                        "Datum einde geldigheid is gelijk aan of gelegen na de datum zoals opgenomen "
                        "onder Datum begin geldigheid."
                    )
                )

    def _clean_geldigheid(self, zaaktype):
        """
        De begin_datum is gelijk aan een Versiedatum van het gerelateerde zaaktype.

        De datum_einde_geldigheid is gelijk aan of gelegen na de datum zoals opgenomen
        onder 'Datum begin geldigheid resultaattype’.
        De datum is gelijk aan de dag voor een Versiedatum van het gerelateerde zaaktype.
        """
        if zaaktype is None:  # can't run any validation on nothing...
            return

        if self.datum_begin_geldigheid != zaaktype.versiedatum:
            raise ValidationError(
                _(
                    "De datum_begin_geldigheid moet gelijk zijn aan een "
                    "Versiedatum van het gerelateerde zaaktype."
                )
            )

        if self.datum_einde_geldigheid:
            if self.datum_einde_geldigheid + timedelta(days=1) != zaaktype.versiedatum:
                raise ValidationError(
                    _(
                        "'Datum einde geldigheid' moet gelijk zijn aan de dag "
                        "voor een Versiedatum van het gerelateerde zaaktype."
                    )
                )


class ConceptMixin(models.Model):
    concept = models.BooleanField(
        _("concept"),
        default=True,
        help_text=_(
            "Geeft aan of het object een concept betreft. Concepten zijn niet-definitieve "
            "versies en zouden niet gebruikt moeten worden buiten deze API."
        ),
        db_index=True,
    )

    class Meta:
        abstract = True
