# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.views.generic import TemplateView

DEFAULT_VNG_COMPONENTS_BRANCH = "stable/1.0.x"


class ComponentIndexView(TemplateView):
    template_name = "index.html"
    # custom context
    github_ref = DEFAULT_VNG_COMPONENTS_BRANCH
    component = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"component": self.component, "github_ref": self.github_ref})
        return context
