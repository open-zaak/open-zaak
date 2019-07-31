from datetime import date, datetime
from typing import Union

from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

import isodate
from vng_api_common.constants import BrondatumArchiefprocedureAfleidingswijze
from vng_api_common.models import APICredential

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

        resultaat = self._get_resultaat()
        resultaattype = self._get_resultaattype(resultaat.resultaattype)
        archiefactietermijn = resultaattype['archiefactietermijn']
        if not archiefactietermijn:
            return

        brondatum_archiefprocedure = resultaattype['brondatumArchiefprocedure']
        afleidingswijze = brondatum_archiefprocedure['afleidingswijze']
        datum_kenmerk = brondatum_archiefprocedure['datumkenmerk']
        objecttype = brondatum_archiefprocedure['objecttype']
        procestermijn = brondatum_archiefprocedure['procestermijn']

        # FIXME: nasty side effect
        orig_value = self.zaak.einddatum
        self.zaak.einddatum = self.datum_status_gezet.date()
        brondatum = get_brondatum(self.zaak, afleidingswijze, datum_kenmerk, objecttype, procestermijn)
        self.zaak.einddatum = orig_value
        if not brondatum:
            return

        return brondatum + isodate.parse_duration(archiefactietermijn)

    def get_archiefnominatie(self) -> str:
        resultaat = self._get_resultaat()
        resultaattype = self._get_resultaattype(resultaat.resultaattype)
        return resultaattype['archiefnominatie']

    def _get_resultaattype(self, resultaattype_url: str):
        if not hasattr(self, '_resultaattype'):
            self._resultaattype = None
            if resultaattype_url:
                Client = import_string(settings.ZDS_CLIENT_CLASS)
                client = Client.from_url(resultaattype_url)
                client.auth = APICredential.get_auth(
                    resultaattype_url,
                    scopes=['zds.scopes.zaaktypes.lezen']
                )
                self._resultaattype = client.retrieve('resultaattype', url=resultaattype_url)
        return self._resultaattype

    def _get_resultaat(self):
        if not hasattr(self, '_resultaat'):
            self._resultaat = self.zaak.resultaat
        return self._resultaat


def get_brondatum(zaak: Zaak, afleidingswijze: str, datum_kenmerk: str=None,
                  objecttype: str=None, procestermijn: str=None) -> date:
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
                _('Geen datumkenmerk aanwezig om de eigenschap te achterhalen voor het bepalen van de brondatum.'))

        eigenschap = zaak.zaakeigenschap_set.filter(_naam=datum_kenmerk).first()
        if eigenschap:
            if not eigenschap.waarde:
                return None

            try:
                return parse_isodatetime(eigenschap.waarde).date()
            except ValueError:
                raise DetermineProcessEndDateException(
                    _('Geen geldige datumwaarde in eigenschap "{}": {}').format(datum_kenmerk, eigenschap.waarde))
        else:
            raise DetermineProcessEndDateException(
                _('Geen eigenschap gevonden die overeenkomt met het datumkenmerk "{}" voor het bepalen van de '
                  'brondatum.').format(datum_kenmerk))

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.ander_datumkenmerk:
        # The brondatum, and therefore the archiefactiedatum, needs to be determined manually.
        return None

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.zaakobject:
        if not objecttype:
            raise DetermineProcessEndDateException(
                _('Geen objecttype aanwezig om het zaakobject te achterhalen voor het bepalen van de brondatum.'))
        if not datum_kenmerk:
            raise DetermineProcessEndDateException(
                _('Geen datumkenmerk aanwezig om het attribuut van het zaakobject te achterhalen voor het bepalen '
                  'van de brondatum.'))

        for zaak_object in zaak.zaakobject_set.filter(object_type=objecttype):
            object = zaak_object._get_object()
            if datum_kenmerk in object:
                try:
                    return parse_isodatetime(object[datum_kenmerk]).date()
                except ValueError:
                    raise DetermineProcessEndDateException(
                        _('Geen geldige datumwaarde in attribuut "{}": {}').format(
                            datum_kenmerk, object[datum_kenmerk]))

        raise DetermineProcessEndDateException(
            _('Geen attribuut gevonden die overeenkomt met het datumkenmerk "{}" voor het bepalen van de '
              'brondatum.').format(datum_kenmerk))

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.termijn:
        if zaak.einddatum is None:
            # TODO: Not sure if we should raise an error instead.
            return None
        if procestermijn is None:
            raise DetermineProcessEndDateException(
                _('Geen procestermijn aanwezig voor het bepalen van de brondatum.'))
        try:
            return zaak.einddatum + isodate.parse_duration(procestermijn)
        except (ValueError, TypeError) as e:
            raise DetermineProcessEndDateException(
                _('Geen geldige periode in procestermijn: {}').format(procestermijn))

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.gerelateerde_zaak:
        # TODO: Determine what this means...
        raise NotImplementedError

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit:
        zaakbesluiten = zaak.zaakbesluit_set.all()
        if not zaakbesluiten.exists():
            # Cannot use ingangsdatum_besluit if Zaak has no Besluiten
            raise DetermineProcessEndDateException(
                _('Geen besluiten aan zaak gekoppeld om brondatum uit af te leiden.')
            )

        Client = import_string(settings.ZDS_CLIENT_CLASS)
        client = Client.from_url(zaakbesluiten.first().besluit)
        client.auth = APICredential.get_auth(zaakbesluiten.first().besluit)

        max_ingangsdatum = None
        for zaakbesluit in zaakbesluiten:
            related_besluit = client.retrieve('besluit', url=zaakbesluit.besluit)
            ingangsdatum = datetime.strptime(related_besluit['ingangsdatum'], '%Y-%m-%d')
            if not max_ingangsdatum or ingangsdatum > max_ingangsdatum:
                max_ingangsdatum = ingangsdatum
        return max_ingangsdatum

    elif afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.vervaldatum_besluit:
        # TODO: Relation from Zaak to Besluit is not implemented yet...
        raise NotImplementedError

    raise ValueError(f'Onbekende "Afleidingswijze": {afleidingswijze}')
