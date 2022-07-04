# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from notifications_api_common.kanalen import Kanaal

from ..models import Besluit

KANAAL_BESLUITEN = Kanaal(
    "besluiten",
    main_resource=Besluit,
    kenmerken=("verantwoordelijke_organisatie", "besluittype"),
)
