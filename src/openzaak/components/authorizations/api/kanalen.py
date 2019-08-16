from vng_api_common.authorizations.models import Applicatie
from vng_api_common.notifications.kanalen import Kanaal

KANAAL_AUTORISATIES = Kanaal(
    'autorisaties',
    main_resource=Applicatie,
    kenmerken=()
)
