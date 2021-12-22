# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from extra_views import ModelFormSetView
from zgw_consumers.constants import AuthTypes
from zgw_consumers.models import NLXConfig, Service

from openzaak.components.autorisaties.admin_views import get_form_data

from .forms import (
    ExternalServiceForm,
    InternalServiceForm,
    NLXConfigForm,
    get_nlx_choices,
)
from .models import InternalService
from .utils import AdminRequiredMixin


class ConfigDetailView(AdminRequiredMixin, TemplateView):
    template_name = "admin/config_detail.html"
    login_url = "admin:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nlx = NLXConfig.get_solo()
        context["nlx"] = nlx

        internal_services = InternalService.objects.order_by("api_type").all()
        context["internal_services"] = internal_services

        external_services = Service.objects.order_by("api_type", "api_root").all()
        context["external_services"] = external_services
        return context


class WizardMixin:
    next_url = None
    previous_url = None
    submit_url = None

    def get_success_url(self):
        if "next" in self.request.POST and self.next_url:
            self.success_url = f"{self.next_url}?wizard=true"
        else:
            self.success_url = self.submit_url

        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "next_url": self.next_url,
                "previous_url": self.previous_url,
                "submit_url": self.submit_url,
            }
        )
        return context


class NLXConfigView(WizardMixin, AdminRequiredMixin, UpdateView):
    model = NLXConfig
    form_class = NLXConfigForm
    template_name = "admin/config_nlx.html"
    next_url = reverse_lazy("config:config-internal")
    submit_url = reverse_lazy("config:config-detail")

    def get_object(self, queryset=None):
        nlx = NLXConfig.get_solo()
        return nlx


class InternalConfigView(WizardMixin, AdminRequiredMixin, ModelFormSetView):
    model = InternalService
    queryset = InternalService.objects.order_by("api_type")
    form_class = InternalServiceForm
    factory_kwargs = {"extra": 0}
    template_name = "admin/config_internal.html"
    next_url = reverse_lazy("config:config-external")
    previous_url = reverse_lazy("config:config-nlx")
    submit_url = reverse_lazy("config:config-detail")


class ExternalConfigView(WizardMixin, AdminRequiredMixin, ModelFormSetView):
    model = Service
    queryset = Service.objects.order_by("api_type", "api_root")
    form_class = ExternalServiceForm
    factory_kwargs = {"extra": 0, "can_delete": True}
    template_name = "admin/config_external.html"
    previous_url = reverse_lazy("config:config-internal")
    submit_url = reverse_lazy("config:config-detail")

    def get_context_data(self, **kwargs):
        formset = kwargs.pop("formset", self.get_formset())
        kwargs["formset"] = formset

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "formdata": [get_form_data(form) for form in formset],
                "nlx_choices": get_nlx_choices(),
                "nlx_outway": NLXConfig.get_solo().outway,
                "auth_types": AuthTypes.choices,
                "formset_config": {
                    "prefix": formset.prefix,
                    "extra": formset.extra,
                    **{
                        field.name: int(field.value())
                        for field in formset.management_form
                    },
                },
            }
        )
        return context
