from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from formtools.wizard.views import SessionWizardView

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


class ConfigWizardView(AdminRequiredMixin, SessionWizardView):
    form_list = [("nlx", NLXConfigForm)]
    templates = {"nlx": "config/config_wizard_nlx.html"}

    def get_template_names(self):
        return [self.templates[self.steps.current]]

    def get_form_instance(self, step):
        if step == "nlx":
            return NLXConfig.get_solo()

        return super().get_form_instance(step)

    def done(self, form_list, form_dict, **kwargs):
        nlx = form_dict["nlx"]
        nlx.save()
        return HttpResponseRedirect(reverse("config-detail"))

    def post(self, *args, **kwargs):
        cancel = self.request.POST.get("cancel", None)
        if cancel:
            return HttpResponseRedirect(reverse("config-detail"))
        return super().post(*args, **kwargs)
