# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from maykin_common.api_reference.views import (
    ComponentIndexView as BaseComponentIndexView,
)


class ComponentIndexView(BaseComponentIndexView):
    template_name = "index.html"
