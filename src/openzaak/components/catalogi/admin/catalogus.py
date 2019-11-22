from django.apps import apps
from django.contrib import admin, messages
from django.core.management import CommandError, call_command
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import EditInlineAdminMixin, ListObjectActionsAdminMixin

from ..models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakInformatieobjectType,
    ZaakType,
)
from .besluittype import BesluitTypeAdmin
from .forms import CatalogusImportForm
from .informatieobjecttype import InformatieObjectTypeAdmin
from .zaaktypen import ZaakTypeAdmin


class ZaakTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakType
    fields = ZaakTypeAdmin.list_display
    fk_name = "catalogus"


class BesluitTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitType
    fields = BesluitTypeAdmin.list_display


class InformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = InformatieObjectType
    fields = InformatieObjectTypeAdmin.list_display
    fk_name = "catalogus"


@admin.register(Catalogus)
class CatalogusAdmin(ListObjectActionsAdminMixin, admin.ModelAdmin):
    model = Catalogus

    # List
    list_display = ("domein", "rsin", "uuid")
    list_filter = ("domein", "rsin")
    ordering = ("domein", "rsin")
    search_fields = ("domein", "rsin", "contactpersoon_beheer_naam")

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("domein", "rsin")}),
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

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="catalogi_catalogus_import",
            )
        ]
        return my_urls + urls

    def import_view(self, request):
        form = CatalogusImportForm(request.POST, request.FILES)
        context = dict(self.admin_site.each_context(request), form=form)
        if "_import" in request.POST:
            if form.is_valid():
                try:
                    call_command("import", form.cleaned_data["file"])
                    self.message_user(
                        request,
                        _("Catalogus successfully imported"),
                        level=messages.SUCCESS,
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalogi_catalogus_changelist")
                    )
                except CommandError as exc:
                    self.message_user(request, exc, level=messages.ERROR)
        return TemplateResponse(request, "import_catalogus.html", context)

    def get_related_objects(self, obj):
        resources = {}

        resources["Catalogus"] = [obj.pk]

        # Resources with foreign keys to catalogus
        fields = ["InformatieObjectType", "BesluitType", "ZaakType"]
        for field in fields:
            resources[field] = list(
                getattr(obj, f"{field.lower()}_set").values_list("pk", flat=True)
            )
        resources["ZaakInformatieobjectType"] = list(
            ZaakInformatieobjectType.objects.filter(
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
                resource_list.append([resource])
                id_list.append([",".join(str(id) for id in ids)])

        return resource_list, id_list

    def response_post_save_change(self, request, obj):
        if "_export" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            resource_list, id_list = self.get_related_objects(obj)
            call_command(
                "export", f"{obj.domein}.zip", resource=resource_list, ids=id_list,
            )

            self.message_user(
                request,
                _(f"Catalogus {obj} was successfully exported"),
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)

    def get_object_actions(self, obj):
        return (
            (
                _("Toon {}").format(ZaakType._meta.verbose_name_plural),
                self._build_changelist_url(ZaakType, query={"catalogus": obj.pk}),
            ),
            (
                _("Toon {}").format(BesluitType._meta.verbose_name_plural),
                self._build_changelist_url(BesluitType, query={"catalogus": obj.pk}),
            ),
            (
                _("Toon {}").format(InformatieObjectType._meta.verbose_name_plural),
                self._build_changelist_url(
                    InformatieObjectType, query={"catalogus": obj.pk}
                ),
            ),
        )
