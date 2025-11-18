# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from vng_api_common.notifications import RoutingHandler, auth, log

from openzaak.components.autorisaties.api.kanalen import KANAAL_AUTORISATIES
from openzaak.notifications.handler_objecten import handle as objects_handler

KANAAL_OBJECTEN = "objecten"
default = RoutingHandler(
    {KANAAL_AUTORISATIES: auth, KANAAL_OBJECTEN: objects_handler}, default=log
)

handle = default
