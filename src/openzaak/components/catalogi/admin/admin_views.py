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

from openzaak.utils.admin import AdminContextMixin

from ..models import BesluitType, Catalogus, InformatieObjectType
from .forms import BesluitTypeFormSet, InformatieObjectTypeFormSet, ZaakTypeImportForm
from .utils import (
    construct_besluittypen,
    construct_iotypen,
    import_zaaktype_for_catalogus,
    retrieve_besluittypen,
    retrieve_iotypen,
)


class CatalogusZaakTypeImportUploadView(
    AdminContextMixin, PermissionRequiredMixin, FormView
):
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


class CatalogusZaakTypeImportSelectView(
    AdminContextMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "admin/catalogi/select_existing_typen.html"
    permission_required = "catalogi.add_zaaktype"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        catalogus_pk = kwargs.get("catalogus_pk")
        catalogus = Catalogus.objects.get(pk=catalogus_pk)

        iotypen = self.request.session.get("iotypen")
        if iotypen and "iotype_forms" not in context:
            iot_dict = {
                obj.omschrijving: obj.pk
                for obj in InformatieObjectType.objects.filter(catalogus=catalogus)
                .order_by("omschrijving", "-datum_begin_geldigheid")
                .distinct("omschrijving")
            }

            iotypen = sorted(iotypen, key=lambda x: x["omschrijving"])
            iotype_forms = InformatieObjectTypeFormSet(
                initial=[
                    {"existing": iot_dict.get(instance["omschrijving"])}
                    for instance in iotypen
                ],
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
        if besluittypen and "besluittype_forms" not in context:
            besluittypen_dict = {
                obj.omschrijving: obj.pk
                for obj in BesluitType.objects.filter(catalogus=catalogus)
                .order_by("omschrijving", "-datum_begin_geldigheid")
                .distinct("omschrijving")
            }
            besluittypen = sorted(besluittypen, key=lambda x: x[0]["omschrijving"])
            besluittype_forms = BesluitTypeFormSet(
                initial=[
                    {"existing": besluittypen_dict.get(instance["omschrijving"])}
                    for instance, uuids in besluittypen
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

        if "iotype-TOTAL_FORMS" in request.POST:
            iotype_forms = InformatieObjectTypeFormSet(request.POST, prefix="iotype",)
        else:
            iotype_forms = None

        if "besluittype-TOTAL_FORMS" in request.POST:
            besluittype_forms = BesluitTypeFormSet(request.POST, prefix="besluittype",)
        else:
            besluittype_forms = None

        try:
            with transaction.atomic():
                iotypen_uuid_mapping = {}
                if iotype_forms:
                    if iotype_forms.is_valid():
                        iotypen_uuid_mapping = construct_iotypen(
                            request.session["iotypen"],
                            iotype_forms.cleaned_data,
                            iotype_forms,
                        )

                besluittypen_uuid_mapping = {}
                if besluittype_forms:
                    besluittype_forms = BesluitTypeFormSet(
                        request.POST, prefix="besluittype"
                    )
                    if besluittype_forms.is_valid():
                        besluittypen_uuid_mapping = construct_besluittypen(
                            request.session["besluittypen"],
                            besluittype_forms.cleaned_data,
                            iotypen_uuid_mapping,
                            besluittype_forms,
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

        catalogus_pk = kwargs.get("catalogus_pk")
        catalogus = Catalogus.objects.get(pk=catalogus_pk)

        if iotype_forms:
            for i, form in zip(request.session["iotypen"], iotype_forms.forms):
                form._bound_fields_cache["existing"].label = (
                    str(catalogus) + " - " + i["omschrijving"]
                )
            kwargs["iotype_forms"] = iotype_forms

        if besluittype_forms:
            for i, form in zip(
                request.session["besluittypen"], besluittype_forms.forms
            ):
                form._bound_fields_cache["existing"].label = (
                    str(catalogus) + " - " + i[0]["omschrijving"]
                )
            kwargs["besluittype_forms"] = besluittype_forms

        context = self.get_context_data(**kwargs)
        return TemplateResponse(request, self.template_name, context)
