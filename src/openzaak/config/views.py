from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from formtools.wizard.views import SessionWizardView

from .forms import NLXConfigForm
from .models import NLXConfig


class ConfigDetailView(TemplateView):
    template_name = "config/config_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nlx = NLXConfig.get_solo()
        context["nlx"] = nlx

        return context


class ConfigWizardView(SessionWizardView):
    template_name = 'config/config_wizard.html'
    form_list = [("nlx", NLXConfigForm)]

    def get_form_instance(self, step):
        if step == "nlx":
            return NLXConfig.get_solo()

        return super().get_form_instance(step)

    def done(self, form_list, form_dict, **kwargs):
        nlx = form_dict["nlx"]
        nlx.save()
        return HttpResponseRedirect(reverse("config-detail"))
