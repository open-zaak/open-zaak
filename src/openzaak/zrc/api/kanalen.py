from vng_api_common.notifications.kanalen import Kanaal

from openzaak.zrc.datamodel.models import Zaak

KANAAL_ZAKEN = Kanaal(
    'zaken',
    main_resource=Zaak,
    kenmerken=(
        'bronorganisatie',
        'zaaktype',
        'vertrouwelijkheidaanduiding'
    )
)
