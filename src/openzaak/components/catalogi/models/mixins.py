# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, timedelta
from typing import Optional

from django.contrib.admin import display
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


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

    omschrijving_field = "omschrijving"

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
        if self._has_overlap:
            raise ValidationError(
                f"{self._meta.verbose_name} versies (dezelfde omschrijving) mogen geen "
                "overlappende geldigheid hebben."
            )

    @property
    def _has_overlap(self):
        from openzaak.components.catalogi.utils import has_overlapping_objects

        try:
            catalogus = self.catalogus
        except self.__class__.catalogus.RelatedObjectDoesNotExist:
            return False
        concept = getattr(self, "concept", None)

        return has_overlapping_objects(
            model_manager=self._meta.default_manager,
            catalogus=catalogus,
            omschrijving_query={
                self.omschrijving_field: getattr(self, self.omschrijving_field)
            },
            begin_geldigheid=self.datum_begin_geldigheid,
            einde_geldigheid=self.datum_einde_geldigheid,
            instance=self,
            concept=concept,
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

    @property
    def begin_object(self) -> date:
        # annotated in the queryset
        if hasattr(self, "datum_begin_object"):
            return self.datum_begin_object

        # for inclusions we don't have annotated queryset
        return (
            self._meta.default_manager.filter(
                **{self.omschrijving_field: getattr(self, self.omschrijving_field)}
            )
            .order_by("datum_begin_geldigheid")
            .first()
            .datum_begin_geldigheid
        )

    @property
    def einde_object(self) -> Optional[date]:
        # annotated in the queryset
        if hasattr(self, "datum_einde_object"):
            return self.datum_einde_object

        # for inclusions we don't have annotated queryset
        return (
            self._meta.default_manager.filter(
                **{self.omschrijving_field: getattr(self, self.omschrijving_field)}
            )
            .order_by("-datum_begin_geldigheid")
            .first()
            .datum_einde_geldigheid
        )


class OptionalGeldigheidMixin(models.Model):
    """
    used for sub-resources of ZaakType
    """

    # nullable datum_begin_geldigheid is weird, but it's how it is in the Standard
    datum_begin_geldigheid = models.DateField(
        _("datum begin geldigheid"),
        blank=True,
        null=True,
        help_text=_("De datum waarop het is ontstaan."),
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
        super().clean()

        if self.datum_einde_geldigheid and self.datum_begin_geldigheid:
            if self.datum_einde_geldigheid < self.datum_begin_geldigheid:
                raise ValidationError(
                    _(
                        "Datum einde geldigheid is gelijk aan of gelegen na de datum zoals opgenomen "
                        "onder Datum begin geldigheid."
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

    def publish(self):
        self.concept = False
        self.clean()
        self.save()

    @display(boolean=True, description=_("gepubliceerd"))
    def is_published(self):
        return not self.concept
