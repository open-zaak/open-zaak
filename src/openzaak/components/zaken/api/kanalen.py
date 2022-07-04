# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from notifications_api_common.kanalen import Kanaal

from ..models import Zaak

KANAAL_ZAKEN = Kanaal(
    "zaken",
    main_resource=Zaak,
    kenmerken=("bronorganisatie", "zaaktype", "vertrouwelijkheidaanduiding"),
)
