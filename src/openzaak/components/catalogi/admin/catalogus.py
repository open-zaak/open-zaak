from django.apps import apps
from django.contrib import admin, messages
from django.core.management import CommandError
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from .besluittype import BesluitTypeAdmin
from .forms import BesluitTypeFormSet, InformatieObjectTypeFormSet, ZaakTypeImportForm
from .informatieobjecttype import InformatieObjectTypeAdmin
from .mixins import ExportMixin, ImportMixin
from .utils import (
    construct_besluittypen,
    construct_iotypen,
    import_zaaktype_for_catalogus,
    retrieve_iotypen_and_besluittypen,
)
from .zaaktypen import ZaakTypeAdmin


class ZaakTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakType
    fields = (
        "zaaktype_omschrijving",
        "identificatie",
        "versiedatum",
    )
    fk_name = "catalogus"


class BesluitTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitType
    fields = (
        "omschrijving",
        "besluitcategorie",
        "catalogus",
    )


class InformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = InformatieObjectType
    fields = (
        "omschrijving",
        "catalogus",
    )
    fk_name = "catalogus"


@admin.register(Catalogus)
class CatalogusAdmin(
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    ExportMixin,
    ImportMixin,
    admin.ModelAdmin,
):
    model = Catalogus
    change_list_template = "admin/catalogi/change_list_catalogus.html"
    change_form_template = "admin/catalogi/change_form_catalogus.html"

    # List
    list_display = ("_admin_name", "domein", "rsin")
    list_filter = ("domein", "rsin")
    ordering = ("domein", "rsin")
    search_fields = (
        "uuid",
        "_admin_name",
        "domein",
        "rsin",
        "contactpersoon_beheer_naam",
    )

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("_admin_name", "domein", "rsin")}),
        (
            _("Contactpersoon beheer"),
            {
                "fields": (
                    "contactpersoon_beheer_naam",
                    "contactpersoon_beheer_telefoonnummer",
                    "contactpersoon_beheer_emailadres",
                )
            },
        ),
    )
    inlines = (ZaakTypeInline, BesluitTypeInline, InformatieObjectTypeInline)

    # For import/export mixins
    resource_name = "catalogus"

    def get_related_objects(self, obj):
        resources = {}

        resources["Catalogus"] = [obj.pk]

        # Resources with foreign keys to catalogus
        fields = ["InformatieObjectType", "BesluitType", "ZaakType"]
        for field in fields:
            resources[field] = list(
                getattr(obj, f"{field.lower()}_set").values_list("pk", flat=True)
            )
        resources["ZaakTypeInformatieObjectType"] = list(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype__in=resources["ZaakType"],
                informatieobjecttype__in=resources["InformatieObjectType"],
            ).values_list("pk", flat=True)
        )

        # Resources with foreign keys to  ZaakType
        fields = ["ResultaatType", "RolType", "StatusType", "Eigenschap"]
        for field in fields:
            model = apps.get_model("catalogi", field)
            resources[field] = list(
                model.objects.filter(zaaktype__in=resources["ZaakType"]).values_list(
                    "pk", flat=True
                )
            )

        resource_list = []
        id_list = []
        for resource, ids in resources.items():
            if ids:
                resource_list.append(resource)
                id_list.append(ids)

        return resource_list, id_list

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<path:catalogus_pk>/zaaktype/import/",
                self.admin_site.admin_view(self.import_view_zaaktype),
                name=f"catalogi_catalogus_import_zaaktype",
            )
        ]
        return my_urls + urls

    def import_view_zaaktype(self, request, catalogus_pk):
        context = dict(self.admin_site.each_context(request), form=ZaakTypeImportForm())
        if "_import_zaaktype" in request.POST:
            form = ZaakTypeImportForm(request.POST, request.FILES)
            if form.is_valid():
                import_file = form.cleaned_data["file"]
                self.file_content = import_file.read()
                (self.iotypen, self.besluittypen,) = retrieve_iotypen_and_besluittypen(
                    catalogus_pk, self.file_content
                )
                context["catalogus_pk"] = catalogus_pk
                catalogus = Catalogus.objects.get(pk=catalogus_pk)

                if self.iotypen:
                    iotype_forms = InformatieObjectTypeFormSet(
                        initial=[
                            {"new_instance": instance} for instance in self.iotypen
                        ],
                        form_kwargs={
                            "catalogus_pk": catalogus_pk,
                            "labels": [
                                str(catalogus) + " - " + i["omschrijving"]
                                for i in self.iotypen
                            ],
                        },
                        prefix="iotype",
                    )
                    context["iotype_forms"] = iotype_forms

                if self.besluittypen:
                    besluittype_forms = BesluitTypeFormSet(
                        initial=[
                            {"new_instance": instance}
                            for instance, uuids in self.besluittypen
                        ],
                        form_kwargs={
                            "catalogus_pk": catalogus_pk,
                            "labels": [
                                str(catalogus) + " - " + i["omschrijving"]
                                for i, uuids in self.besluittypen
                            ],
                        },
                        prefix="besluittype",
                    )
                    context["besluittype_forms"] = besluittype_forms

                if self.besluittypen or self.iotypen:
                    return TemplateResponse(
                        request, f"admin/catalogi/select_existing_typen.html", context,
                    )
                else:
                    try:
                        with transaction.atomic():
                            import_zaaktype_for_catalogus(
                                catalogus_pk, self.file_content, {}, {}
                            )

                        self.message_user(
                            request,
                            _("ZaakType successfully imported"),
                            level=messages.SUCCESS,
                        )
                        return HttpResponseRedirect(
                            reverse(f"admin:catalogi_catalogus_changelist")
                        )
                    except CommandError as exc:
                        self.message_user(request, exc, level=messages.ERROR)
        elif "_select" in request.POST:
            try:
                with transaction.atomic():
                    iotypen_uuid_mapping = {}
                    if "iotype-TOTAL_FORMS" in request.POST:
                        iotype_forms = InformatieObjectTypeFormSet(
                            request.POST, prefix="iotype"
                        )
                        if iotype_forms.is_valid():
                            iotypen_uuid_mapping = construct_iotypen(
                                self.iotypen, iotype_forms.cleaned_data
                            )

                    besluittypen_uuid_mapping = {}
                    if "besluittype-TOTAL_FORMS" in request.POST:
                        besluittype_forms = BesluitTypeFormSet(
                            request.POST, prefix="besluittype"
                        )
                        if besluittype_forms.is_valid():
                            besluittypen_uuid_mapping = construct_besluittypen(
                                self.besluittypen,
                                besluittype_forms.cleaned_data,
                                iotypen_uuid_mapping,
                            )
                    import_zaaktype_for_catalogus(
                        catalogus_pk,
                        self.file_content,
                        iotypen_uuid_mapping,
                        besluittypen_uuid_mapping,
                    )

                self.message_user(
                    request,
                    _("ZaakType successfully imported"),
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(
                    reverse(f"admin:catalogi_catalogus_changelist")
                )
            except (CommandError, IntegrityError) as exc:
                self.message_user(request, exc, level=messages.ERROR)
        return TemplateResponse(
            request, f"admin/catalogi/import_zaaktype.html", context
        )

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(ZaakType, obj),
            link_to_related_objects(BesluitType, obj),
            link_to_related_objects(InformatieObjectType, obj),
        )
