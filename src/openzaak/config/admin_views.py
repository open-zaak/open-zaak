from django.conf import settings
from django.urls import reverse
from django.views.generic import TemplateView

from .models import InternalService, NLXConfig
from .utils import AdminRequiredMixin


class NLXInwayView(AdminRequiredMixin, TemplateView):
    template_name = "admin/nlx_inway.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        generic = {
            "documentation_url": "https://open-zaak.readthedocs.io/en/latest/",
        }
        version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]
        services = []
        for internal_service in InternalService.objects.filter(nlx=True).order_by(
            "api_type"
        ):
            component = internal_service.component
            api_root_url = reverse(
                f"api-root-{internal_service.component}", kwargs={"version": version}
            )
            schema_url = reverse(
                f"schema-json-{component}",
                kwargs={"version": version, "format": ".yaml"},
            )
            service = {
                "name": component,
                "endpoint_url": self.request.build_absolute_uri(api_root_url),
                "api_specification_document_url": self.request.build_absolute_uri(
                    schema_url
                ),
            }
            service.update(generic)
            services.append(service)

        context.update({"services": services})

        return context


class ConfigDetailView(AdminRequiredMixin, TemplateView):
    template_name = "admin/config_detail.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nlx = NLXConfig.get_solo()
        context["nlx"] = nlx

        internal_services = InternalService.objects.order_by("api_type").all()
        context["internal_services"] = internal_services

        return context
