# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from notifications_api_common.kanalen import Kanaal
from vng_api_common.authorizations.models import Applicatie

KANAAL_AUTORISATIES = Kanaal("autorisaties", main_resource=Applicatie, kenmerken=())
