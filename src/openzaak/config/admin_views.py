from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.sites.models import Site
from django.urls import reverse
from django.views.generic import TemplateView


class NLXConfigView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "admin/nlx_config.html"
    login_url = "admin:login"

    def test_func(self):
        user = self.request.user
        return (
            user.is_superuser
            or user.groups.filter(name__in=["Admin", "API admin"]).exists()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        site = Site.objects.get_current(self.request)
        protocol = "http{}".format("s" if settings.IS_HTTPS else "")
        base_url = f"{protocol}://{site.domain}"

        generic = {
            "documentation_url": "https://open-zaak.readthedocs.io/en/latest/",
        }
        version = settings.REST_FRAMEWORK["DEFAULT_VERSION"]

        services = []
        for component in [
            "autorisaties",
            "besluiten",
            "catalogi",
            "documenten",
            "zaken",
        ]:
            api_root_url = reverse(f"api-root-{component}", kwargs={"version": version})
            schema_url = reverse(
                f"schema-json-{component}",
                kwargs={"version": version, "format": ".json"},
            )
            service = {
                "name": component.title(),
                "endpoint_url": f"{base_url}{api_root_url}",
                "api_specification_document_url": f"{base_url}{schema_url}",
            }
            service.update(generic)
            services.append(service)

        context.update({"services": services})

        return context
