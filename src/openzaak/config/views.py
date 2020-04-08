from django.urls import reverse_lazy

from extra_views import ModelFormSetView

from .forms import InternalServiceForm
from .models import InternalService
from .utils import AdminRequiredMixin


class InternalConfigView(AdminRequiredMixin, ModelFormSetView):
    model = InternalService
    queryset = InternalService.objects.order_by("api_type")
    form_class = InternalServiceForm
    factory_kwargs = {"extra": 0}
    template_name = "config/config_internal.html"
    success_url = reverse_lazy("config-detail")
