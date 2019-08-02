from django.conf import settings

from vng_api_common.notifications.kanalen import Kanaal

from openzaak.components.documenten.models import EnkelvoudigInformatieObject

KANAAL_DOCUMENTEN = Kanaal(
    'documenten',
    main_resource=EnkelvoudigInformatieObject,
    kenmerken=(
        'bronorganisatie',
        'informatieobjecttype',
        'vertrouwelijkheidaanduiding'
    )
)
