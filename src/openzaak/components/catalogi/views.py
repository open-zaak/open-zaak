from django.core.management import call_command
from django.http import HttpResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView


class DumpDataView(TemplateView):
    template_name = "catalogi/dumpdata.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fixture_url"] = self.request.build_absolute_uri(
            reverse("dumpdata-fixture")
        )
        return context


class DumpDataFixtureView(View):
    """
    Offer a dumpdata-download as fixture.
    """

    def get(self, request):
        response = HttpResponse(content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="fixture.json"'
        call_command("dumpdata", args=["datamodel"], indent=4, stdout=response)
        return response
