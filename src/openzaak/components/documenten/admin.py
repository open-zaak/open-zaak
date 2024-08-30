# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import forms
from django.conf import settings
from django.contrib import admin
from django.db.models import CharField, F
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _

from privates.admin import PrivateMediaMixin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    AuditTrailInlineAdminMixin,
    CMISAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from .api import viewsets
from .constants import ObjectInformatieObjectTypes
from .models import (
    BestandsDeel,
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
    Verzending,
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

    def has_delete_permission(self, request, obj=None):
        if settings.CMIS_ENABLED:
            return False
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if settings.CMIS_ENABLED:
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if settings.CMIS_ENABLED:
            return False
        return super().has_change_permission(request, obj)


class ObjectInformatieObjectForm(forms.ModelForm):
    class Meta:
        model = ObjectInformatieObject
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        object_type = cleaned_data.get("object_type")

        if (
            object_type == ObjectInformatieObjectTypes.zaak
            and not cleaned_data.get("_zaak")
            and not cleaned_data.get("_zaak_base_url")
        ):
            raise forms.ValidationError(
                "Je moet een zaak opgeven: "
                "selecteer een zaak of vul een externe URL in."
            )

        if (
            object_type == ObjectInformatieObjectTypes.besluit
            and not cleaned_data.get("_besluit")
            and not cleaned_data.get("_besluit_base_url")
        ):
            raise forms.ValidationError(
                "Je moet een besluit opgeven: "
                "selecteer een besluittype of vul een externe URL in."
            )

        if object_type == ObjectInformatieObjectTypes.verzoek and not cleaned_data.get(
            "verzoek"
        ):
            raise forms.ValidationError(
                "Je moet een verzoek opgeven: vul een externe URL in."
            )

        return cleaned_data


@admin.register(ObjectInformatieObject)
class ObjectInformatieObjectAdmin(
    AuditTrailAdminMixin, CMISAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    form = ObjectInformatieObjectForm
    list_display = ("informatieobject", "object_type", "get_object_display")
    list_filter = ("object_type",)
    list_select_related = ("informatieobject", "_zaak", "_besluit", "_object_base_url")
    search_fields = (
        "uuid",
        "informatieobject__enkelvoudiginformatieobject__uuid",
        "informatieobject__enkelvoudiginformatieobject__identificatie",
        "_zaak__uuid",
        "_zaak__identificatie",
        "_besluit__uuid",
        "_besluit__identificatie",
        "object_url",
        "verzoek",
    )
    ordering = ("informatieobject",)
    raw_id_fields = ("informatieobject", "_zaak", "_besluit", "_object_base_url")
    viewset = viewsets.ObjectInformatieObject

    @admin.display(description="object")
    def get_object_display(self, obj):
        return obj._zaak or obj._besluit or obj._object_url

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            object_url=Concat(
                F("_object_base_url__api_root"),
                F("_object_relative_url"),
                output_field=CharField(),
            )
        )


@admin.register(Verzending)
class VerzendingAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = (
        "uuid",
        "aard_relatie",
        "contactpersoonnaam",
        "verzenddatum",
        "ontvangstdatum",
    )
    list_filter = (
        "aard_relatie",
        "informatieobject",
    )
    ordering = (
        "-verzenddatum",
        "-ontvangstdatum",
    )
    search_fields = (
        "contactpersoonnaam",
        "uuid",
    )
    raw_id_fields = ("informatieobject",)

    readonly_fields = ("uuid",)

    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "uuid",
                    "aard_relatie",
                    "toelichting",
                    "verzenddatum",
                    "ontvangstdatum",
                    "betrokkene",
                    "informatieobject",
                ),
            },
        ),
        (
            _("Contactpersoon"),
            {
                "fields": (
                    "contact_persoon",
                    "contactpersoonnaam",
                ),
            },
        ),
        (
            _("Afwijkend binnenlands correspondentieadres verzending"),
            {
                "fields": (
                    "binnenlands_correspondentieadres_huisletter",
                    "binnenlands_correspondentieadres_huisnummer",
                    "binnenlands_correspondentieadres_huisnummer_toevoeging",
                    "binnenlands_correspondentieadres_naam_openbare_ruimte",
                    "binnenlands_correspondentieadres_postcode",
                    "binnenlands_correspondentieadres_woonplaatsnaam",
                ),
            },
        ),
        (
            _("Afwijkend buitenlands correspondentieadres verzending"),
            {
                "fields": (
                    "buitenlands_correspondentieadres_adres_buitenland_1",
                    "buitenlands_correspondentieadres_adres_buitenland_2",
                    "buitenlands_correspondentieadres_adres_buitenland_3",
                    "buitenlands_correspondentieadres_land_postadres",
                ),
            },
        ),
        (
            _("Afwijkend correspondentie postadres verzending"),
            {
                "fields": (
                    "buitenlands_correspondentiepostadres_postbus_of_antwoord_nummer",
                    "buitenlands_correspondentiepostadres_postadres_postcode",
                    "buitenlands_correspondentiepostadres_postadrestype",
                    "buitenlands_correspondentiepostadres_woonplaatsnaam",
                ),
            },
        ),
    )


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

    @admin.display(description="object")
    def get_object_display(self, obj):
        return obj._zaak or obj._zaak_url or obj._besluit or obj._besluit_url


class VerzendingInline(EditInlineAdminMixin, admin.TabularInline):
    model = Verzending
    fields = VerzendingAdmin.list_display
    fk_name = "informatieobject"


class EnkelvoudigInformatieObjectInline(
    AuditTrailInlineAdminMixin, PrivateMediaMixin, admin.StackedInline
):
    model = EnkelvoudigInformatieObject
    raw_id_fields = ("canonical", "_informatieobjecttype")
    readonly_fields = ("uuid",)
    extra = 0
    min_num = 1
    verbose_name = _("versie")
    verbose_name_plural = _("versies")
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet
    private_media_fields = ("inhoud",)
    private_media_view_class = PrivateMediaView
    private_media_file_widget = PrivateFileWidget


def unlock(modeladmin, request, queryset):
    queryset.update(lock="")


@admin.register(EnkelvoudigInformatieObjectCanonical)
class EnkelvoudigInformatieObjectCanonicalAdmin(AuditTrailAdminMixin, admin.ModelAdmin):
    list_display = ["__str__", "get_not_lock_display"]
    inlines = [
        EnkelvoudigInformatieObjectInline,
        GebruiksrechtenInline,
        ObjectInformatieObjectInline,
        VerzendingInline,
    ]
    actions = [unlock]

    @admin.display(
        description="free to change",
        boolean=True,
    )
    def get_not_lock_display(self, obj) -> bool:
        return not bool(obj.lock)

    def get_viewset(self, request):
        return None


class EnkelvoudigInformatieObjectForm(forms.ModelForm):
    class Meta:
        model = EnkelvoudigInformatieObject
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_informatieobjecttype") and not cleaned_data.get(
            "_informatieobjecttype_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een informatieobjecttype opgeven: "
                "selecteer een informatieobjecttype uit de catalogus of vul een externe URL in."
            )

        return cleaned_data


@admin.register(EnkelvoudigInformatieObject)
class EnkelvoudigInformatieObjectAdmin(
    AuditTrailAdminMixin,
    CMISAdminMixin,
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
    raw_id_fields = (
        "canonical",
        "_informatieobjecttype",
        "_informatieobjecttype_base_url",
    )
    viewset = viewsets.EnkelvoudigInformatieObjectViewSet
    private_media_fields = ("inhoud",)
    private_media_view_class = PrivateMediaView
    private_media_file_widget = PrivateFileWidget
    form = EnkelvoudigInformatieObjectForm
    list_select_related = ("canonical",)

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
            {
                "fields": (
                    "_informatieobjecttype_base_url",
                    "_informatieobjecttype_relative_url",
                    "_informatieobjecttype",
                )
            },
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
                    "verschijningsvorm",
                    "trefwoorden",
                )
            },
        ),
        (
            _("Verzending/ontvangst"),
            {
                "fields": (
                    "ontvangstdatum",
                    "verzenddatum",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Ondertekening"),
            {
                "fields": (
                    "ondertekening_soort",
                    "ondertekening_datum",
                ),
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

    def get_object(self, request, object_id, from_field=None):
        if from_field is None and settings.CMIS_ENABLED:
            from_field = "uuid"
        return super().get_object(request, object_id, from_field=from_field)

    @admin.display(
        description=_("locked"),
        boolean=True,
    )
    def _locked(self, obj) -> bool:
        return obj.locked

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(Gebruiksrechten, obj.canonical),
            link_to_related_objects(ObjectInformatieObject, obj.canonical),
            link_to_related_objects(Verzending, obj.canonical),
        )


@admin.register(BestandsDeel)
class BestandsDeelAdmin(PrivateMediaMixin, admin.ModelAdmin):
    list_display = (
        "__str__",
        "informatieobject",
        "volgnummer",
        "voltooid",
        "datetime_created",
    )
    list_filter = ("informatieobject",)
    private_media_fields = ("inhoud",)
