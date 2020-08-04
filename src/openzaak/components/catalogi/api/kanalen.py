# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from vng_api_common.notifications.kanalen import Kanaal

from ..models import BesluitType, InformatieObjectType, ZaakType

KANAAL_BESLUITTYPEN = Kanaal(
    "besluittypen", main_resource=BesluitType, kenmerken=("catalogus",)
)

KANAAL_INFORMATIEOBJECTTYPEN = Kanaal(
    "informatieobjecttypen",
    main_resource=InformatieObjectType,
    kenmerken=("catalogus",),
)

KANAAL_ZAAKTYPEN = Kanaal("zaaktypen", main_resource=ZaakType, kenmerken=("catalogus",))
