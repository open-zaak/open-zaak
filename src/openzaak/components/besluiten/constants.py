from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from vng_api_common.constants import ObjectTypes


class VervalRedenen(DjangoChoices):
    tijdelijk = ChoiceItem("tijdelijk", label=_("Besluit met tijdelijke werking"))
    ingetrokken_overheid = ChoiceItem(
        "ingetrokken_overheid", label=_("Besluit ingetrokken door overheid")
    )
    ingetrokken_belanghebbende = ChoiceItem(
        "ingetrokken_belanghebbende",
        label=_("Besluit ingetrokken o.v.v. belanghebbende"),
    )


# TODO Should be moved to vng-api-common
class RelatieAarden(DjangoChoices):
    hoort_bij = ChoiceItem("hoort_bij", _("Hoort bij, omgekeerd: kent"))
    legt_vast = ChoiceItem(
        "legt_vast", _("Legt vast, omgekeerd: kan vastgelegd zijn als")
    )

    @classmethod
    def from_object_type(cls, object_type: str) -> str:
        if object_type == ObjectTypes.zaak:
            return cls.hoort_bij

        if object_type == ObjectTypes.besluit:
            return cls.legt_vast

        raise ValueError(f"Unknown object_type '{object_type}'")
