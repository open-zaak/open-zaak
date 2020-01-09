from django.conf import settings

from django.contrib.sites.models import Site
from django.views.generic import TemplateView


class NLXConfigView(TemplateView):
    template_name = "admin/nlx_config.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        site = Site.objects.get_current(self.request)
        protocol = "http{}".format("s" if settings.IS_HTTPS else "")
        base_url = f"{protocol}://{site.domain}/"

        generic = {
            "documentation_url": "https://open-zaak.readthedocs.io/en/latest/",
        }
        services = [
            {
                "name": "Autorisaties",
                "endpoint_url": f"{base_url}/zaken/api/v1/",
                "api_specification_document_url": f"{base_url}/zaken/api/v1/schema/openapi.json",
            },
            {
                "name": "Besluiten",
                "endpoint_url": f"{base_url}/besluiten/api/v1/",
                "api_specification_document_url": f"{base_url}/besluiten/api/v1/schema/openapi.json",
            },
            {
                "name": "Catalogi",
                "endpoint_url": f"{base_url}/catalogi/api/v1/",
                "api_specification_document_url": f"{base_url}/catalogi/api/v1/schema/openapi.json",
            },
            {
                "name": "Documenten",
                "endpoint_url": f"{base_url}/documenten/api/v1/",
                "api_specification_document_url": f"{base_url}/documenten/api/v1/schema/openapi.json",
            },
            {
                "name": "Zaken",
                "endpoint_url": f"{base_url}/zaken/api/v1/",
                "api_specification_document_url": f"{base_url}/zaken/api/v1/schema/openapi.json",
            },
        ]

        context.update({
            "services": services
        })

        return context
