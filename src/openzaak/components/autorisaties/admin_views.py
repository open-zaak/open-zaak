from typing import Dict

from django import forms
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView

from vng_api_common.authorizations.models import Applicatie, Autorisatie

from openzaak.components.catalogi.models import Catalogus

from .admin_serializers import CatalogusSerializer
from .forms import (
    COMPONENT_TO_PREFIXES_MAP,
    AutorisatieFormSet,
    RelatedTypeSelectionMethods,
    VertrouwelijkheidsAanduiding,
    get_scope_choices,
)


def form_with_errors(form: forms.Form) -> Dict[str, Dict]:
    errors = {
        field: [{"msg": error.message, "code": error.code} for error in _errors]
        for field, _errors in form.errors.as_data().items()
    }
    values = {field.name: field.value() for field in form}
    return {
        "errors": errors,
        "values": values,
    }


class AutorisatiesView(DetailView):
    model = Applicatie
    template_name = "admin/autorisaties/applicatie_autorisaties.html"
    pk_url_kwarg = "object_id"
    # set these on the .as_viev(...) call
    admin_site = None
    model_admin = None

    # perform permission checks
    def dispatch(self, request, *args, **kwargs):
        assert self.admin_site
        assert self.model_admin

        applicatie = self.get_object()
        if not self.model_admin.has_change_permission(request, applicatie):
            raise PermissionDenied()

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = applicatie = self.get_object()
        formset = AutorisatieFormSet(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect(
                "admin:autorisaties_applicatie_change", args=(applicatie.pk,)
            )

        formdata = [form_with_errors(form) for form in formset]
        context = self.get_context_data(formset=formset, formdata=formdata)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.setdefault("formset", AutorisatieFormSet())
        context.setdefault("formdata", [])

        catalogi = Catalogus.objects.prefetch_related(
            "zaaktype_set", "informatieobjecttype_set", "besluittype_set",
        )

        context.update(self.admin_site.each_context(self.request))
        context.update(
            {
                "opts": Applicatie._meta,
                "original": self.get_object(),
                "title": _("beheer autorisaties"),
                "is_popup": False,
                "formset": AutorisatieFormSet(),
                "scope_choices": get_scope_choices(),
                "COMPONENTS_TO_PREFIXES_MAP": COMPONENT_TO_PREFIXES_MAP,
                "RELATED_TYPE_SELECTION_METHODS": RelatedTypeSelectionMethods.choices,
                "VA_CHOICES": VertrouwelijkheidsAanduiding.choices,
                "catalogi": CatalogusSerializer(
                    catalogi, read_only=True, many=True
                ).data,
            }
        )

        return context
