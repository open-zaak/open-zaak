from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices

# Waardenverzameling nemen we letterlijk over. Dit betekend dat we onder
# andere de volgende waarden verwachten (en kleine afwijking hiervan zal dus
# niet valideren):
#
# Eigenschap.formaat: 'datum/tijd (jjjjmmdduummss)' dus inclusief het deel tussen haakjes
# ZaakType.vertrouwelijkheidsaanduiding: 'ZEER GEHEIM' (dus geheel in hoofdletters met spatie)
# ResultaatType.archiefnominatie: 'Blijvend bewaren' (alleen eerste is hoofdletter en een spatie)
# ResultaatType.brondatum_archiefprocedure: 'afgehandeld' dus geheel met kleine letters


class FormaatChoices(DjangoChoices):
    tekst = ChoiceItem('tekst', _('Tekst'))
    getal = ChoiceItem('getal', _('Getal'))
    datum = ChoiceItem('datum', _('Datum'))
    datum_tijd = ChoiceItem('datum_tijd', _('Datum/tijd'))


class ArchiefProcedure(DjangoChoices):
    afgehandeld = ChoiceItem('afgehandeld', _('Afgehandeld'))
    ingangsdatum_besluit = ChoiceItem('ingangsdatum_besluit', _('Ingangsdatum besluit'))
    vervaldatum_besluit = ChoiceItem('vervaldatum_besluit', _('Vervaldatum besluit'))
    eigenschap = ChoiceItem('eigenschap', _('Eigenschap'))
    ander_datumkenmerk = ChoiceItem('ander_datumkenmerk', _('Ander datumkenmerk'))


class InternExtern(DjangoChoices):
    intern = ChoiceItem('intern', _('Intern'))
    extern = ChoiceItem('extern', _('Extern'))


class RichtingChoices(DjangoChoices):
    inkomend = ChoiceItem('inkomend', _('Inkomend'))
    intern = ChoiceItem('intern', _('Intern'))
    uitgaand = ChoiceItem('uitgaand', _('Uitgaand'))


class ArchiefNominatieChoices(DjangoChoices):
    blijvend_bewaren = ChoiceItem('blijvend_bewaren', _('Blijvend bewaren'))
    vernietigen = ChoiceItem('vernietigen', _('Vernietigen'))


class AardRelatieChoices(DjangoChoices):
    vervolg = ChoiceItem('vervolg', _('Vervolg'))  # een zaak van het ZAAKTYPE is een te plannen vervolg op een zaak van het andere ZAAKTYPE
    bijdrage = ChoiceItem('bijdrage', _('Bijdrage'))  # een zaak van het ZAAKTYPE levert een bijdrage aan het bereiken van de uitkomst van een zaak van het andere ZAAKTYPE
    onderwerp = ChoiceItem('onderwerp', _('Onderwerp'))  # een zaak van het ZAAKTYPE heeft betrekking op een zaak van het andere ZAAKTYPE of een zaak van het andere ZAAKTYPE is relevant voor of is onderwerp van een zaak van het ZAAKTYPE
