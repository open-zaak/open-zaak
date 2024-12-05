# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.db import transaction
from django.db.utils import IntegrityError
from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, TemplateView

from openzaak.utils.admin import AdminContextMixin

from ..api.viewsets import ZaakTypeViewSet
from ..models import BesluitType, Catalogus, InformatieObjectType, ZaakType
from ..validators import validate_zaaktype_for_publish
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

            request.session["identificatie_prefix"] = request.POST.get(
                "identificatie_prefix"
            )

            request.session["generate_new_uuids"] = request.POST.get(
                "generate_new_uuids"
            )

            iotypen = retrieve_iotypen(catalogus_pk, request.session["file_content"])
            request.session["iotypen"] = (
                sorted(iotypen, key=lambda x: x["omschrijving"]) if iotypen else iotypen
            )

            besluittypen = retrieve_besluittypen(
                catalogus_pk, request.session["file_content"]
            )
            request.session["besluittypen"] = (
                sorted(besluittypen, key=lambda x: x[0]["omschrijving"])
                if besluittypen
                else besluittypen
            )

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
                            request.session["identificatie_prefix"],
                            catalogus_pk,
                            request.session["file_content"],
                            {},
                            {},
                            request.session["generate_new_uuids"],
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
        if iotypen:

            form_kwargs = {
                "catalogus_pk": catalogus_pk,
                "labels": [str(catalogus) + " - " + i["omschrijving"] for i in iotypen],
            }
            prefix = "iotype"

            if self.request.POST:
                iotype_forms = InformatieObjectTypeFormSet(
                    self.request.POST, form_kwargs=form_kwargs, prefix=prefix
                )
            else:
                iot_dict = {
                    obj.omschrijving: obj.pk
                    for obj in InformatieObjectType.objects.filter(catalogus=catalogus)
                    .order_by("omschrijving", "-datum_begin_geldigheid")
                    .distinct("omschrijving")
                }
                iotype_forms = InformatieObjectTypeFormSet(
                    initial=[
                        {"existing": iot_dict.get(instance["omschrijving"])}
                        for instance in iotypen
                    ],
                    form_kwargs=form_kwargs,
                    prefix=prefix,
                )

            context["iotype_forms"] = iotype_forms

        besluittypen = self.request.session.get("besluittypen")
        if besluittypen:
            form_kwargs = {
                "catalogus_pk": catalogus_pk,
                "labels": [
                    str(catalogus) + " - " + i["omschrijving"]
                    for i, uuids in besluittypen
                ],
            }
            prefix = "besluittype"

            if self.request.POST:
                besluittype_forms = BesluitTypeFormSet(
                    self.request.POST, form_kwargs=form_kwargs, prefix=prefix
                )
            else:
                besluittypen_dict = {
                    obj.omschrijving: obj.pk
                    for obj in BesluitType.objects.filter(catalogus=catalogus)
                    .order_by("omschrijving", "-datum_begin_geldigheid")
                    .distinct("omschrijving")
                }
                besluittype_forms = BesluitTypeFormSet(
                    initial=[
                        {"existing": besluittypen_dict.get(instance["omschrijving"])}
                        for instance, uuids in besluittypen
                    ],
                    form_kwargs=form_kwargs,
                    prefix=prefix,
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

                if context.get("iotype_forms"):
                    iotype_forms = context["iotype_forms"]
                    if iotype_forms.is_valid():
                        iotypen_uuid_mapping = construct_iotypen(
                            request.session["iotypen"],
                            iotype_forms.cleaned_data,
                            iotype_forms,
                            request.session["generate_new_uuids"],
                        )

                besluittypen_uuid_mapping = {}
                if context.get("besluittype_forms"):
                    besluittype_forms = context["besluittype_forms"]
                    if besluittype_forms.is_valid():
                        besluittypen_uuid_mapping = construct_besluittypen(
                            request.session["besluittypen"],
                            besluittype_forms.cleaned_data,
                            iotypen_uuid_mapping,
                            besluittype_forms,
                            request.session["generate_new_uuids"],
                        )

                import_zaaktype_for_catalogus(
                    request.session["identificatie_prefix"],
                    kwargs["catalogus_pk"],
                    request.session["file_content"],
                    iotypen_uuid_mapping,
                    besluittypen_uuid_mapping,
                    request.session["generate_new_uuids"],
                )

            messages.add_message(
                request, messages.SUCCESS, _("ZaakType successfully imported")
            )
            return HttpResponseRedirect(reverse("admin:catalogi_catalogus_changelist"))
        except (CommandError, IntegrityError, ValidationError) as exc:
            messages.add_message(request, messages.ERROR, exc)

        return TemplateResponse(request, self.template_name, context)


class ZaaktypePublishView(AdminContextMixin, PermissionRequiredMixin, DetailView):
    template_name = "admin/catalogi/publish_zaaktype.html"
    permission_required = "catalogi.change_zaaktype"

    queryset = ZaakType.objects.all().prefetch_related(
        "besluittypen", "informatieobjecttypen"
    )
    pk_url_kwarg = "zaaktype_pk"

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()
        self.errors = []

        if not self.object.concept:
            messages.add_message(
                request, messages.WARNING, _("Zaaktype object is already published.")
            )
        else:
            with transaction.atomic():
                if "_auto-publish" in request.POST:
                    self.auto_publish(request)

                for field, error in validate_zaaktype_for_publish(self.object):
                    self.errors.append(error)

                # if any errors
                if len(self.errors) > 0:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        " | ".join([str(e) for e in self.errors]),
                    )
                    return self.render_to_response(self.get_context_data())

                try:
                    self.object.publish()
                except ValidationError as e:
                    messages.add_message(request, messages.ERROR, e.message)
                    return self.render_to_response(self.get_context_data())

            messages.add_message(
                request,
                messages.SUCCESS,
                _("The resource has been published successfully!"),
            )
            self.send_notification(request)

        return HttpResponseRedirect(
            reverse("admin:catalogi_zaaktype_change", args=(self.object.pk,))
        )

    def auto_publish(self, request):
        published_besluittypen = []
        published_informatieobjecttypen = []

        # publish related types
        for besluittype in self.object.besluittypen.filter(concept=True):
            try:
                besluittype.publish()
                published_besluittypen.append(besluittype.omschrijving)
            except ValidationError as e:
                self.errors.append(f"{besluittype.omschrijving} – {e.message}")

        for iot in self.object.informatieobjecttypen.filter(concept=True):
            try:
                iot.publish()
                published_informatieobjecttypen.append(iot.omschrijving)
            except ValidationError as e:
                self.errors.append(f"{iot.omschrijving} – {e.message}")

        if len(published_besluittypen) > 0:
            messages.add_message(
                request,
                messages.INFO,
                _("Auto-published related besluittypen: {besluittypen}").format(
                    besluittypen=", ".join(published_besluittypen)
                ),
                "autopublish",
            )
        if len(published_informatieobjecttypen) > 0:
            messages.add_message(
                request,
                messages.INFO,
                _("Auto-published related informatieobjecttypen: {iots}").format(
                    iots=", ".join(published_informatieobjecttypen)
                ),
                "autopublish",
            )

    def send_notification(self, context_request):

        viewset = ZaakTypeViewSet(request=self.request)
        viewset.action = "update"

        reference_object = self.object

        # set versioning to context_request
        (
            context_request.version,
            context_request.versioning_scheme,
        ) = viewset.determine_version(context_request)

        data = viewset.serializer_class(
            reference_object, context={"request": context_request}
        ).data

        viewset.notify(status_code=200, data=data, instance=reference_object)
