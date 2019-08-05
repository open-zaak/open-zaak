from django.conf import settings

from openzaak.components.besluiten.models import Besluit
from vng_api_common.notifications.kanalen import Kanaal

KANAAL_BESLUITEN = Kanaal(
    'besluiten',
    main_resource=Besluit,
    kenmerken=(
        'verantwoordelijke_organisatie',
        'besluittype',
    )
)
