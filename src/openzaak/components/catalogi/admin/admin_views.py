# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.management import CommandError
from django.db import transaction
from django.db.utils import IntegrityError
from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView

from ..models import Catalogus
from .forms import BesluitTypeFormSet, InformatieObjectTypeFormSet, ZaakTypeImportForm
from .utils import (
    construct_besluittypen,
    construct_iotypen,
    import_zaaktype_for_catalogus,
    retrieve_besluittypen,
    retrieve_iotypen,
)


class CatalogusZaakTypeImportUploadView(PermissionRequiredMixin, FormView):
    template_name = "admin/catalogi/import_zaaktype.html"
    form_class = ZaakTypeImportForm
    permission_required = "catalogi.add_zaaktype"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        catalogus_pk = kwargs.get("catalogus_pk")
        context = self.get_context_data(**kwargs)
        if form.is_valid():
            import_file = form.cleaned_data["file"]
            request.session["file_content"] = import_file.read()

            iotypen = retrieve_iotypen(catalogus_pk, request.session["file_content"])
            request.session["iotypen"] = iotypen

            besluittypen = retrieve_besluittypen(
                catalogus_pk, request.session["file_content"]
            )
            request.session["besluittypen"] = besluittypen

            if besluittypen or iotypen:
                return HttpResponseRedirect(
                    reverse(
                        "admin:catalogi_catalogus_import_zaaktype_select",
                        kwargs={"catalogus_pk": catalogus_pk},
                    )
                )
            else:
                try:
                    with transaction.atomic():
                        import_zaaktype_for_catalogus(
                            catalogus_pk, request.session["file_content"], {}, {}
                        )

                    messages.add_message(
                        request, messages.SUCCESS, _("ZaakType successfully imported")
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalogi_catalogus_changelist")
                    )
                except CommandError as exc:
                    messages.add_message(request, messages.ERROR, exc)
        return TemplateResponse(request, self.template_name, context)


class CatalogusZaakTypeImportSelectView(PermissionRequiredMixin, TemplateView):
    template_name = "admin/catalogi/select_existing_typen.html"
    permission_required = "catalogi.add_zaaktype"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        catalogus_pk = kwargs.get("catalogus_pk")
        catalogus = Catalogus.objects.get(pk=catalogus_pk)

        iotypen = self.request.session.get("iotypen")
        if iotypen:
            iotype_forms = InformatieObjectTypeFormSet(
                initial=[{"new_instance": instance} for instance in iotypen],
                form_kwargs={
                    "catalogus_pk": catalogus_pk,
                    "labels": [
                        str(catalogus) + " - " + i["omschrijving"] for i in iotypen
                    ],
                },
                prefix="iotype",
            )
            context["iotype_forms"] = iotype_forms

        besluittypen = self.request.session.get("besluittypen")
        if besluittypen:
            besluittype_forms = BesluitTypeFormSet(
                initial=[
                    {"new_instance": instance} for instance, uuids in besluittypen
                ],
                form_kwargs={
                    "catalogus_pk": catalogus_pk,
                    "labels": [
                        str(catalogus) + " - " + i["omschrijving"]
                        for i, uuids in besluittypen
                    ],
                },
                prefix="besluittype",
            )
            context["besluittype_forms"] = besluittype_forms
        return context

    def get(self, request, *args, **kwargs):
        if "file_content" not in request.session:
            return HttpResponseRedirect(
                reverse(
                    "admin:catalogi_catalogus_import_zaaktype",
                    kwargs={"catalogus_pk": kwargs["catalogus_pk"]},
                )
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        try:
            with transaction.atomic():
                iotypen_uuid_mapping = {}
                if "iotype-TOTAL_FORMS" in request.POST:
                    iotype_forms = InformatieObjectTypeFormSet(
                        request.POST, prefix="iotype"
                    )
                    if iotype_forms.is_valid():
                        iotypen_uuid_mapping = construct_iotypen(
                            request.session["iotypen"], iotype_forms.cleaned_data
                        )

                besluittypen_uuid_mapping = {}
                if "besluittype-TOTAL_FORMS" in request.POST:
                    besluittype_forms = BesluitTypeFormSet(
                        request.POST, prefix="besluittype"
                    )
                    if besluittype_forms.is_valid():
                        besluittypen_uuid_mapping = construct_besluittypen(
                            request.session["besluittypen"],
                            besluittype_forms.cleaned_data,
                            iotypen_uuid_mapping,
                        )

                import_zaaktype_for_catalogus(
                    kwargs["catalogus_pk"],
                    request.session["file_content"],
                    iotypen_uuid_mapping,
                    besluittypen_uuid_mapping,
                )

            messages.add_message(
                request, messages.SUCCESS, _("ZaakType successfully imported")
            )
            return HttpResponseRedirect(reverse("admin:catalogi_catalogus_changelist"))
        except (CommandError, IntegrityError) as exc:
            messages.add_message(request, messages.ERROR, exc)
        return TemplateResponse(request, self.template_name, context)
