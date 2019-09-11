from openzaak.components.besluiten.models import Besluit


class ZaakBesluit(Besluit):
    class Meta:
        proxy = True

    @property
    def besluit(self):
        return self
