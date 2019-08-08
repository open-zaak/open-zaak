from openzaak.components.zaken.models import Zaak
from vng_api_common.notifications.kanalen import Kanaal

KANAAL_ZAKEN = Kanaal(
    'zaken',
    main_resource=Zaak,
    kenmerken=(
        'bronorganisatie',
        'zaaktype',
        'vertrouwelijkheidaanduiding'
    )
)
