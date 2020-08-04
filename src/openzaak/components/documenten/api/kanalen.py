# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.notifications.kanalen import Kanaal

from ..models import EnkelvoudigInformatieObject

KANAAL_DOCUMENTEN = Kanaal(
    "documenten",
    main_resource=EnkelvoudigInformatieObject,
    kenmerken=(
        "bronorganisatie",
        "informatieobjecttype",
        "vertrouwelijkheidaanduiding",
    ),
)
