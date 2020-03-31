from django.urls import reverse_lazy

from extra_views import ModelFormSetView
from zgw_consumers.models import Service

from .forms import ExternalServiceForm
from .utils import AdminRequiredMixin


class ExternalConfigView(AdminRequiredMixin, ModelFormSetView):
    model = Service
    queryset = Service.objects.order_by("api_type", "api_root")
    form_class = ExternalServiceForm
    factory_kwargs = {"extra": 1}
    template_name = "config/config_external.html"
    success_url = reverse_lazy("config-detail")
