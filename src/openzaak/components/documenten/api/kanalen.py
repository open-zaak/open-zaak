from django.conf import settings

from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from vng_api_common.notifications.kanalen import Kanaal

KANAAL_DOCUMENTEN = Kanaal(
    'documenten',
    main_resource=EnkelvoudigInformatieObject,
    kenmerken=(
        'bronorganisatie',
        'informatieobjecttype',
        'vertrouwelijkheidaanduiding'
    )
)
