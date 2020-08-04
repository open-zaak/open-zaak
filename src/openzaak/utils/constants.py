# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from vng_api_common.constants import ComponentTypes

COMPONENT_MAPPING = {
    "autorisaties": ComponentTypes.ac,
    "zaken": ComponentTypes.zrc,
    "catalogi": ComponentTypes.ztc,
    "documenten": ComponentTypes.drc,
    "besluiten": ComponentTypes.brc,
}
