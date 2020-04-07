from django.urls import reverse_lazy

from extra_views import ModelFormSetView
from zgw_consumers.constants import AuthTypes
from zgw_consumers.models import Service

from openzaak.components.autorisaties.admin_views import get_form_data

from .forms import (
    ExternalServiceForm,
    get_nlx_choices,
)
from .utils import AdminRequiredMixin


class ExternalConfigView(AdminRequiredMixin, ModelFormSetView):
    model = Service
    queryset = Service.objects.order_by("api_type", "api_root")
    form_class = ExternalServiceForm
    factory_kwargs = {"extra": 0}
    template_name = "config/config_external.html"
    success_url = reverse_lazy("config-detail")

    def get_context_data(self, **kwargs):
        formset = kwargs.pop("formset", self.get_formset())
        kwargs["formset"] = formset

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "formdata": [get_form_data(form) for form in formset],
                "nlx_choices": get_nlx_choices(),
                "nlx_outway": NLXConfig.get_solo().outway,
                "auth_types": AuthTypes.choices,
                "formset_config": {
                    "prefix": formset.prefix,
                    "extra": formset.extra,
                    **{
                        field.name: int(field.value())
                        for field in formset.management_form
                    },
                },
            }
        )

        return context
