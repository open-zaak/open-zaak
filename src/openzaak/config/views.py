from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from .forms import NLXConfigForm
from .models import NLXConfig
from .utils import AdminRequiredMixin


class ConfigDetailView(AdminRequiredMixin, TemplateView):
    template_name = "config/config_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nlx = NLXConfig.get_solo()
        context["nlx"] = nlx

        return context


class ConfigWizardView(AdminRequiredMixin, UpdateView):
    model = NLXConfig
    form_class = NLXConfigForm
    template_name = "config/config_nlx.html"
    success_url = reverse_lazy("config-detail")

    def get_object(self, queryset=None):
        nlx = NLXConfig.get_solo()
        return nlx
