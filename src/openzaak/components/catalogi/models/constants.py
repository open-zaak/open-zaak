from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class SelectielijstKlasseProcestermijn(DjangoChoices):
    nihil = ChoiceItem('nihil', _("Er is geen aparte procestermijn, de bewaartermijn start direct na de procesfase."))
    ingeschatte_bestaansduur_procesobject = ChoiceItem(
        'ingeschatte_bestaansduur_procesobject',
        _("Er wordt een inschatting gemaakt van de maximale bestaans-of geldigheidsduur van het procesobject, "
          "ongeacht de daadwerkelijke duur. Dit kan bijvoorbeeld al vastgelegd worden in het zaaktype, zodat "
          "procestermijn en bewaartermijn samen een bewaartermijn vormen die direct kan gaan lopen na de procesfase.")
    )
