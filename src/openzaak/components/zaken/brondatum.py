# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date, datetime
from typing import Union

from django.db.models import Max
from django.utils.translation import ugettext_lazy as _

from dateutil.relativedelta import relativedelta
from relativedeltafield import parse_relativedelta
from vng_api_common.constants import BrondatumArchiefprocedureAfleidingswijze

from openzaak.utils import parse_isodatetime
from openzaak.utils.exceptions import DetermineProcessEndDateException

from .models import Zaak


class BrondatumCalculator:
    def __init__(self, zaak: Zaak, datum_status_gezet: datetime):
        self.zaak = zaak
        self.datum_status_gezet = datum_status_gezet

    def calculate(self) -> Union[None, date]:
        if self.zaak.archiefactiedatum:
            return

        resultaattype = self.zaak.resultaat.resultaattype

        archiefactietermijn = resultaattype.archiefactietermijn
        if not archiefactietermijn:
            return

        # if loose-fk-field - convert to relative-delta
        if isinstance(archiefactietermijn, str):
            archiefactietermijn = parse_relativedelta(archiefactietermijn)

        brondatum_archiefprocedure = resultaattype.brondatum_archiefprocedure
        afleidingswijze = brondatum_archiefprocedure["afleidingswijze"]
        datum_kenmerk = brondatum_archiefprocedure["datumkenmerk"]
        objecttype = brondatum_archiefprocedure["objecttype"]
        procestermijn = brondatum_archiefprocedure["procestermijn"]
        # if loose-fk-field - convert to relative-delta
        if isinstance(procestermijn, str):
            procestermijn = parse_relativedelta(procestermijn)

        # FIXME: nasty side effect
        orig_value = self.zaak.einddatum
        self.zaak.einddatum = self.datum_status_gezet.date()
        brondatum = get_brondatum(
            self.zaak, afleidingswijze, datum_kenmerk, objecttype, procestermijn
        )
        self.zaak.einddatum = orig_value
        if not brondatum:
            return

        return brondatum + archiefactietermijn

    def get_archiefnominatie(self) -> str:
        resultaattype = self.zaak.resultaat.resultaattype
        return resultaattype.archiefnominatie


def get_brondatum(
    zaak: Zaak,
    afleidingswijze: str,
    datum_kenmerk: str = None,
    objecttype: str = None,
    procestermijn: relativedelta = None,
) -> date:
    """
    To calculate the Archiefactiedatum, we first need the "brondatum" which is like the start date of the storage
    period.

    :param afleidingswijze:
        One of the `Afleidingswijze` choices.
    :param datum_kenmerk:
        A `string` representing an arbitrary attribute name. Currently only needed when `afleidingswijze` is
        `eigenschap` or `zaakobject`.
    :param objecttype:
        A `string` representing an arbitrary objecttype name. Currently only needed when `afleidingswijze` is
        `zaakobject`.
    :param procestermijn:
        A `string` representing an ISO8601 period that is considered the process term of the Zaak. Currently only
        needed when `afleidingswijze` is `termijn`.
    :return:
        A specific date that marks the start of the storage period, or `None`.
    """
    if afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.afgehandeld:
        return zaak.einddatum

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.hoofdzaak:
        # TODO: Document that hoofdzaak can not an external zaak
        return zaak.hoofdzaak.einddatum if zaak.hoofdzaak else None

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.eigenschap:
        if not datum_kenmerk:
            raise DetermineProcessEndDateException(
                _(
                    "Geen datumkenmerk aanwezig om de eigenschap te achterhalen voor het bepalen van de brondatum."
                )
            )

        eigenschap = zaak.zaakeigenschap_set.filter(_naam=datum_kenmerk).first()
        if eigenschap:
            if not eigenschap.waarde:
                return None

            try:
                return parse_isodatetime(eigenschap.waarde).date()
            except ValueError:
                raise DetermineProcessEndDateException(
                    _('Geen geldige datumwaarde in eigenschap "{}": {}').format(
                        datum_kenmerk, eigenschap.waarde
                    )
                )
        else:
            raise DetermineProcessEndDateException(
                _(
                    'Geen eigenschap gevonden die overeenkomt met het datumkenmerk "{}" voor het bepalen van de '
                    "brondatum."
                ).format(datum_kenmerk)
            )

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk:
        # The brondatum, and therefore the archiefactiedatum, needs to be determined manually.
        return None

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.zaakobject:
        if not objecttype:
            raise DetermineProcessEndDateException(
                _(
                    "Geen objecttype aanwezig om het zaakobject te achterhalen voor het bepalen van de brondatum."
                )
            )
        if not datum_kenmerk:
            raise DetermineProcessEndDateException(
                _(
                    "Geen datumkenmerk aanwezig om het attribuut van het zaakobject te achterhalen voor het bepalen "
                    "van de brondatum."
                )
            )

        dates = []
        for zaak_object in zaak.zaakobject_set.filter(object_type=objecttype):
            if zaak_object.object:
                remote_object = zaak_object._get_object()
                value = remote_object.get(datum_kenmerk)
            else:
                local_object = getattr(zaak_object, objecttype.replace("_", ""))
                value = getattr(local_object, datum_kenmerk, None)

            if value is None:
                raise DetermineProcessEndDateException(
                    _("{} geen geldig attribuut voor ZaakObject van type {}").format(
                        datum_kenmerk, objecttype
                    )
                )

            try:
                dates.append(parse_isodatetime(value).date())
            except ValueError:
                raise DetermineProcessEndDateException(
                    _('Geen geldige datumwaarde in attribuut "{}": {}').format(
                        datum_kenmerk, value
                    )
                )

        if dates:
            return max(dates)

        raise DetermineProcessEndDateException(
            _(
                'Geen attribuut gevonden die overeenkomt met het datumkenmerk "{}" voor het bepalen van de '
                "brondatum."
            ).format(datum_kenmerk)
        )

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.termijn:
        if zaak.einddatum is None:
            # TODO: Not sure if we should raise an error instead.
            return None
        if procestermijn is None:
            raise DetermineProcessEndDateException(
                _("Geen procestermijn aanwezig voor het bepalen van de brondatum.")
            )
        try:
            return zaak.einddatum + procestermijn
        except (ValueError, TypeError) as exc:
            raise DetermineProcessEndDateException(
                _("Geen geldige periode in procestermijn: {}").format(procestermijn)
            ) from exc

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak:
        relevante_zaken = zaak.relevante_andere_zaken
        if relevante_zaken.count() == 0:
            # Cannot use ingangsdatum_besluit if Zaak has no Besluiten
            raise DetermineProcessEndDateException(
                _(
                    "Geen gerelateerde zaken aan zaak gekoppeld om brondatum uit af te leiden."
                )
            )

        # internal
        relevante_zaken_internal = Zaak.objects.filter(
            pk__in=relevante_zaken.filter(_relevant_zaak__isnull=False).values_list(
                "_relevant_zaak", flat=True
            )
        )
        einddatum_max_internal = relevante_zaken_internal.aggregate(Max("einddatum"))[
            "einddatum__max"
        ]

        # external
        einddatum_max_external = None
        for relevante_zaak in relevante_zaken.filter(_relevant_zaak__isnull=True):
            einddatum_str = relevante_zaak.url.einddatum
            einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d").date()
            einddatum_max_external = max_with_none(einddatum, einddatum_max_external)

        return max_with_none(einddatum_max_internal, einddatum_max_external)

    elif (
        afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit
    ):
        zaakbesluiten = zaak.besluit_set.all()
        if not zaakbesluiten.exists():
            # Cannot use ingangsdatum_besluit if Zaak has no Besluiten
            raise DetermineProcessEndDateException(
                _("Geen besluiten aan zaak gekoppeld om brondatum uit af te leiden.")
            )

        max_ingangsdatum = zaakbesluiten.aggregate(Max("ingangsdatum"))[
            "ingangsdatum__max"
        ]
        return max_ingangsdatum

    elif (
        afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit
    ):
        zaakbesluiten = zaak.besluit_set.all()
        if not zaakbesluiten.exists():
            # Cannot use vervaldatum_besluit if Zaak has no Besluiten
            raise DetermineProcessEndDateException(
                _("Geen besluiten aan zaak gekoppeld om brondatum uit af te leiden.")
            )

        max_vervaldatum = zaakbesluiten.aggregate(Max("vervaldatum"))[
            "vervaldatum__max"
        ]
        if max_vervaldatum is None:
            raise DetermineProcessEndDateException(
                _(
                    "Besluit.vervaldatum moet gezet worden voordat de zaak kan worden afgesloten"
                )
            )
        return max_vervaldatum

    raise ValueError(f'Onbekende "Afleidingswijze": {afleidingswijze}')


def max_with_none(*args):
    return max(filter(lambda x: x is not None, args)) if any(args) else None
