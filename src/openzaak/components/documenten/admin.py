from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from privates.admin import PrivateMediaMixin
from vng_api_common.constants import ObjectTypes

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from .api import viewsets
from .models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from .views import PrivateMediaView
from .widgets import PrivateFileWidget


@admin.register(Gebruiksrechten)
class GebruiksrechtenAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("informatieobject", "startdatum", "einddatum")
    list_filter = ("startdatum", "einddatum")
    search_fields = (
        "uuid",
        "informatieobject__enkelvoudiginformatieobject__uuid",
        "informatieobject__enkelvoudiginformatieobject__identificatie",
        "omschrijving_voorwaarden",
    )
    date_hierarchy = "startdatum"
    ordering = ("startdatum", "informatieobject")
    raw_id_fields = ("informatieobject",)
    viewset = viewsets.GebruiksrechtenViewSet


class ObjectInformatieObjectForm(forms.ModelForm):
    class Meta:
        model = ObjectInformatieObject
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        object_type = cleaned_data.get("object_type")

        if (
            object_type == ObjectTypes.zaak
            and not cleaned_data.get("_zaak")
            and not cleaned_data.get("_zaak_url")
        ):
            raise forms.ValidationError(
                "Je moet een zaak opgeven: "
                "selecteer een zaak of vul een externe URL in."
            )

        if (
            object_type == ObjectTypes.besluit
            and not cleaned_data.get("_besluit")
            and not cleaned_data.get("_besluit_url")
        ):
            raise forms.ValidationError(
                "Je moet een besluit opgeven: "
                "selecteer een besluittype of vul een externe URL in."
            )

        return cleaned_data


@admin.register(ObjectInformatieObject)
class ObjectInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    form = ObjectInformatieObjectForm
    list_display = ("informatieobject", "object_type", "get_object_display")
    list_filter = ("object_type",)
    list_select_related = ("informatieobject", "_zaak", "_besluit")
    search_fields = (
        "uuid",
        "informatieobject__enkelvoudiginformatieobject__uuid",
        "informatieobject__enkelvoudiginformatieobject__identificatie",
        "_zaak__uuid",
        "_zaak__identificatie",
        "_zaak_url",
        "_besluit__uuid",
        "_besluit__identificatie",
        "_besluit_url",
    )
    ordering = ("informatieobject",)
    raw_id_fields = ("informatieobject", "_zaak", "_besluit")
    viewset = viewsets.ObjectInformatieObject

    def get_object_display(self, obj):
        return obj._zaak or obj._zaak_url or obj._besluit or obj._besluit_url

    get_object_display.short_description = "object"


class GebruiksrechtenInline(EditInlineAdminMixin, admin.TabularInline):
    model = Gebruiksrechten
    fields = GebruiksrechtenAdmin.list_display
    fk_name = "informatieobject"


class ObjectInformatieObjectInline(
    AuditTrailAdminMixin, EditInlineAdminMixin, admin.TabularInline
):
    model = ObjectInformatieObject
    fields = ObjectInformatieObjectAdmin.list_display
    fk_name = "informatieobject"

    def get_object_display(self, obj):
        return obj._zaak or obj._zaak_url or obj._besluit or obj._besluit_url

    get_object_display.short_description = "object"


class EnkelvoudigInformatieObjectInline(
    AuditTrailInlineAdminMixin, admin.StackedInline
):
    model = EnkelvoudigInformatieObject
    raw_id_fields = ("canonical", "_informatieobjecttype")
    readonly_fields = ("uuid",)
    extra = 1
    verbose_name = _("versie")
    verbose_name_plural = _("versies")
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet


def unlock(modeladmin, request, queryset):
    queryset.update(lock="")


@admin.register(EnkelvoudigInformatieObjectCanonical)
class EnkelvoudigInformatieObjectCanonicalAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["__str__", "get_not_lock_display"]
    inlines = [
        EnkelvoudigInformatieObjectInline,
        GebruiksrechtenInline,
        ObjectInformatieObjectInline,
    ]
    actions = [unlock]

    def get_not_lock_display(self, obj) -> bool:
        return not bool(obj.lock)

    get_not_lock_display.short_description = "free to change"
    get_not_lock_display.boolean = True

    def get_viewset(self, request):
        return None


@admin.register(EnkelvoudigInformatieObject)
class EnkelvoudigInformatieObjectAdmin(
    AuditTrailAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    PrivateMediaMixin,
    admin.ModelAdmin,
):
    list_display = (
        "identificatie",
        "bronorganisatie",
        "creatiedatum",
        "titel",
        "versie",
        "_locked",
    )
    list_filter = ("bronorganisatie",)
    search_fields = ("identificatie", "uuid")
    ordering = ("-begin_registratie",)
    date_hierarchy = "creatiedatum"
    raw_id_fields = ("canonical", "_informatieobjecttype")
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet
    private_media_fields = ("inhoud",)

    fieldsets = (
        (
            _("Identificatie"),
            {
                "fields": (
                    "uuid",
                    "identificatie",
                    "canonical",
                    "bronorganisatie",
                    "creatiedatum",
                    "versie",
                )
            },
        ),
        (
            _("Typering"),
            {"fields": ("_informatieobjecttype_url", "_informatieobjecttype",)},
        ),
        (
            _("Documentgegevens"),
            {
                "fields": (
                    "vertrouwelijkheidaanduiding",
                    "titel",
                    "auteur",
                    "status",
                    "beschrijving",
                    "formaat",
                    "taal",
                    "bestandsnaam",
                    "inhoud",
                    "link",
                    "indicatie_gebruiksrecht",
                )
            },
        ),
        (
            _("Verzending/ontvangst"),
            {"fields": ("ontvangstdatum", "verzenddatum",), "classes": ("collapse",),},
        ),
        (
            _("Ondertekening"),
            {
                "fields": ("ondertekening_soort", "ondertekening_datum",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Integriteit"),
            {
                "fields": (
                    "integriteit_algoritme",
                    "integriteit_waarde",
                    "integriteit_datum",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def _locked(self, obj) -> bool:
        return obj.locked

    _locked.boolean = True
    _locked.short_description = _("locked")

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(Gebruiksrechten, obj.canonical),
            link_to_related_objects(ObjectInformatieObject, obj.canonical),
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        private_media_fields = self.get_private_media_fields()
        if db_field.name in private_media_fields:
            view_name = self._get_private_media_view_name(db_field.name)
            obj = self.get_object(
                request, request.resolver_match.kwargs.get("object_id")
            )
            attrs = {}
            if obj:
                display_value = obj.bestandsnaam if obj.bestandsnaam else obj.inhoud.url
                attrs["display_value"] = display_value
            field.widget = PrivateFileWidget(
                url_name="admin:%s" % view_name, attrs=attrs,
            )
        return field

    def get_private_media_view(self, field):
        return PrivateMediaView.as_view(
            model=self.model,
            file_field=field,
            permission_required=self.get_private_media_permission_required(field),
            sendfile_options=self.get_private_media_view_options(field),
        )
