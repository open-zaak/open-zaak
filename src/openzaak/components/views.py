# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from maykin_common.api_reference.views import (
    ComponentIndexView as BaseComponentIndexView,
)


class ComponentIndexView(BaseComponentIndexView):
    template_name = "index.html"
    description = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["description"] = self.description
        return context
