from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from extra_views import ModelFormSetView

from .forms import InternalServiceForm, NLXConfigForm
from .models import InternalService, NLXConfig
from .utils import AdminRequiredMixin


class ConfigDetailView(AdminRequiredMixin, TemplateView):
    template_name = "config/config_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nlx = NLXConfig.get_solo()
        context["nlx"] = nlx

        internal_services = InternalService.objects.order_by("api_type").all()
        context["internal_services"] = internal_services

        return context


class NLXConfigView(AdminRequiredMixin, UpdateView):
    model = NLXConfig
    form_class = NLXConfigForm
    template_name = "config/config_nlx.html"
    success_url = reverse_lazy("config-internal")

    def get_object(self, queryset=None):
        nlx = NLXConfig.get_solo()
        return nlx


class InternalConfigView(AdminRequiredMixin, ModelFormSetView):
    model = InternalService
    queryset = InternalService.objects.order_by("api_type")
    form_class = InternalServiceForm
    factory_kwargs = {"extra": 0}
    template_name = "config/config_internal.html"
    success_url = reverse_lazy("config-detail")
