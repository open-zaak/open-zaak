# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django import forms
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.db.models import CharField, F, Prefetch
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _

from openzaak.forms.widgets import AuthorityAxisOrderOLWidget
from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..api.validators import match_eigenschap_specificatie
from ..constants import AardZaakRelatie
from ..models import (
    KlantContact,
    RelevanteZaakRelatie,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakBesluit,
    ZaakContactMoment,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
    ZaakVerzoek,
)
from ..models.zaken import ZaakKenmerk
from .betrokkenen import (
    MedewerkerInline,
    NatuurlijkPersoonInline,
    NietNatuurlijkPersoonInline,
    OrganisatorischeEenheidInline,
    VestigingInline,
)
from .objecten import (
    AdresInline,
    BuurtInline,
    GemeenteInline,
    GemeentelijkeOpenbareRuimteInline,
    HuishoudenInline,
    InrichtingselementInline,
    KadastraleOnroerendeZaakInline,
    KunstwerkdeelInline,
    MaatschappelijkeActiviteitInline,
    OpenbareRuimteInline,
    OverigeInline,
    PandInline,
    SpoorbaandeelInline,
    TerreindeelInline,
    TerreinGebouwdObjectInline,
    WaterdeelInline,
    WegdeelInline,
    WijkInline,
    WoonplaatsInline,
    WozDeelobjectInline,
    WozObjectInline,
    WozWaardeInline,
    ZakelijkRechtInline,
)


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_statustype") and not cleaned_data.get(
            "_statustype_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een statustype opgeven: "
                "selecteer een statustype uit de catalogus of vul een externe URL in."
            )

        return cleaned_data


@admin.register(Status)
class StatusAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "datum_status_gezet")
    list_select_related = ("zaak", "_statustype", "_statustype_base_url")
    list_filter = ("datum_status_gezet",)
    search_fields = (
        "uuid",
        "zaak__identificatie",
        "zaak__uuid",
        "statustoelichting",
    )
    form = StatusForm
    ordering = ("datum_status_gezet",)
    date_hierarchy = "datum_status_gezet"
    raw_id_fields = ("zaak", "_statustype", "_statustype_base_url", "gezetdoor")
    viewset = "openzaak.components.zaken.api.viewsets.StatusViewSet"


@admin.register(ZaakObject)
class ZaakObjectAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "object_type", "object", "relatieomschrijving")
    list_select_related = ("zaak",)
    list_filter = ("object_type",)
    search_fields = (
        "uuid",
        "object",
        "relatieomschrijving",
        "zaak__identificatie",
        "zaak__uuid",
    )
    ordering = ("object_type", "object")
    raw_id_fields = ("zaak", "_zaakobjecttype_base_url", "_zaakobjecttype")
    viewset = "openzaak.components.zaken.api.viewsets.ZaakObjectViewSet"
    inlines = [
        AdresInline,
        BuurtInline,
        GemeenteInline,
        GemeentelijkeOpenbareRuimteInline,
        HuishoudenInline,
        InrichtingselementInline,
        KadastraleOnroerendeZaakInline,
        KunstwerkdeelInline,
        MaatschappelijkeActiviteitInline,
        OpenbareRuimteInline,
        OverigeInline,
        PandInline,
        SpoorbaandeelInline,
        TerreindeelInline,
        TerreinGebouwdObjectInline,
        WaterdeelInline,
        WegdeelInline,
        WijkInline,
        WoonplaatsInline,
        WozDeelobjectInline,
        WozObjectInline,
        WozWaardeInline,
        ZakelijkRechtInline,
        NatuurlijkPersoonInline,
        NietNatuurlijkPersoonInline,
        OrganisatorischeEenheidInline,
        VestigingInline,
        MedewerkerInline,
    ]


@admin.register(KlantContact)
class KlantContactAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "identificatie", "datumtijd", "kanaal")
    list_select_related = ("zaak",)
    list_filter = ("datumtijd",)
    search_fields = (
        "uuid",
        "identificatie",
        "toelichting",
        "kanaal",
        "zaak__identificatie",
        "zaak__uuid",
    )
    date_hierarchy = "datumtijd"
    ordering = ("-identificatie", "datumtijd")
    raw_id_fields = ("zaak",)
    viewset = "openzaak.components.zaken.api.viewsets.KlantContactViewSet"


class ZaakEigenschapForm(forms.ModelForm):
    class Meta:
        model = ZaakEigenschap
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_eigenschap") and not cleaned_data.get(
            "_eigenschap_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een eigenschap opgeven: "
                "selecteer een eigenschap uit de catalogus of vul een externe URL in."
            )

        # for now check waarde only for local eigenschap
        eigenschap = cleaned_data.get("_eigenschap")
        waarde = cleaned_data.get("waarde")

        if not eigenschap or not waarde:
            return cleaned_data

        if not match_eigenschap_specificatie(
            eigenschap.specificatie_van_eigenschap, waarde
        ):
            raise forms.ValidationError(
                _(
                    "The 'waarde' value doesn't match the related eigenschap.specificatie"
                )
            )

        return cleaned_data


@admin.register(ZaakEigenschap)
class ZaakEigenschapAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = (
        "zaak",
        "_eigenschap",
        "_eigenschap_base_url",
        "_eigenschap_relative_url",
        "waarde",
    )
    list_select_related = ("zaak", "_eigenschap", "_eigenschap_base_url")
    list_filter = ("_naam",)
    search_fields = (
        "uuid",
        "_naam",
        "zaak__identificatie",
        "zaak__uuid",
    )
    form = ZaakEigenschapForm
    ordering = (
        "zaak",
        "_eigenschap",
        "_eigenschap_base_url",
        "_eigenschap_relative_url",
    )
    raw_id_fields = ("zaak", "_eigenschap", "_eigenschap_base_url")
    viewset = "openzaak.components.zaken.api.viewsets.ZaakEigenschapViewSet"


class ZaakInformatieObjectForm(forms.ModelForm):
    class Meta:
        model = ZaakInformatieObject
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_informatieobject") and not cleaned_data.get(
            "_informatieobject_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een informatieobject opgeven: "
                "selecteer een informatieobject of vul een externe URL in."
            )

        return cleaned_data


@admin.register(ZaakInformatieObject)
class ZaakInformatieObjectAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = (
        "zaak",
        "_informatieobject",
        "_informatieobject_base_url",
        "_informatieobject_relative_url",
        "registratiedatum",
        "titel",
        "beschrijving",
    )
    list_select_related = (
        "zaak",
        "_informatieobject",
        "_informatieobject_base_url",
        "status",
    )
    list_filter = ("aard_relatie",)
    search_fields = (
        "uuid",
        "zaak__identificatie",
        "zaak__uuid",
        "_informatieobject__enkelvoudiginformatieobject__uuid",
        "_informatieobject__enkelvoudiginformatieobject__identificatie",
        "informatieobject_url",
    )
    form = ZaakInformatieObjectForm
    date_hierarchy = "registratiedatum"
    ordering = (
        "zaak",
        "_informatieobject",
        "_informatieobject_base_url",
        "_informatieobject_relative_url",
    )
    raw_id_fields = (
        "zaak",
        "_informatieobject",
        "_informatieobject_base_url",
        "status",
    )
    viewset = "openzaak.components.zaken.api.viewsets.ZaakInformatieObjectViewSet"

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            informatieobject_url=Concat(
                F("_informatieobject_base_url__api_root"),
                F("_informatieobject_relative_url"),
                output_field=CharField(),
            )
        )


class ResultaatForm(forms.ModelForm):
    class Meta:
        model = Resultaat
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_resultaattype") and not cleaned_data.get(
            "_resultaattype_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een resultaattype opgeven: "
                "selecteer een resultaattype uit de catalogus of vul een externe URL in."
            )

        return cleaned_data


@admin.register(Resultaat)
class ResultaatAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "toelichting")
    list_select_related = ("zaak", "_resultaattype", "_resultaattype_base_url")
    search_fields = (
        "uuid",
        "toelichting",
        "_resultaattype__uuid",
        "resultaattype_url",
        "zaak__identificatie",
        "zaak__uuid",
    )
    form = ResultaatForm
    ordering = ("zaak",)
    raw_id_fields = ("zaak", "_resultaattype", "_resultaattype_base_url")
    viewset = "openzaak.components.zaken.api.viewsets.ResultaatViewSet"

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            resultaattype_url=Concat(
                F("_resultaattype_base_url__api_root"),
                F("_resultaattype_relative_url"),
                output_field=CharField(),
            )
        )


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_roltype") and not cleaned_data.get(
            "_roltype_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een roltype opgeven: "
                "selecteer een roltype uit de catalogus of vul een externe URL in."
            )

        return cleaned_data


@admin.register(Rol)
class RolAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "betrokkene", "betrokkene_type")
    list_select_related = ("zaak", "_roltype", "_roltype_base_url")
    list_filter = ("betrokkene_type", "indicatie_machtiging", "registratiedatum")
    search_fields = (
        "uuid",
        "zaak__identificatie",
        "zaak__uuid",
        "betrokkene",
        "omschrijving",
        "roltoelichting",
    )
    form = RolForm
    date_hierarchy = "registratiedatum"
    ordering = ("registratiedatum", "betrokkene")
    raw_id_fields = ("zaak", "_roltype", "_roltype_base_url")
    viewset = "openzaak.components.zaken.api.viewsets.RolViewSet"
    inlines = [
        NatuurlijkPersoonInline,
        NietNatuurlijkPersoonInline,
        OrganisatorischeEenheidInline,
        VestigingInline,
        MedewerkerInline,
    ]


class RelevanteZaakRelatieForm(forms.ModelForm):
    class Meta:
        model = RelevanteZaakRelatie
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_relevant_zaak") and not cleaned_data.get(
            "_relevant_zaak_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een relevante zaak opgeven: "
                "selecteer een zaak of vul een externe URL in."
            )

        if cleaned_data.get(
            "aard_relatie"
        ) == AardZaakRelatie.overig and not cleaned_data.get("overige_relatie"):
            raise forms.ValidationError(
                "Het veld `overigeRelatie` is verplicht als de relatie aard `overig` is."
            )

        return cleaned_data


@admin.register(RelevanteZaakRelatie)
class RelevanteZaakRelatieAdmin(admin.ModelAdmin):
    list_display = (
        "zaak",
        "_relevant_zaak",
        "_relevant_zaak_base_url",
        "_relevant_zaak_relative_url",
        "aard_relatie",
    )
    list_filter = ("aard_relatie",)
    search_fields = (
        "zaak__uuid",
        "zaak__identificatie",
        "_relevant_zaak__uuid",
        "_relevant_zaak__identificatie",
        "relevant_zaak_url",
    )
    form = RelevanteZaakRelatieForm
    ordering = (
        "zaak",
        "_relevant_zaak",
        "_relevant_zaak_base_url",
        "_relevant_zaak_relative_url",
    )
    raw_id_fields = ("zaak", "_relevant_zaak", "_relevant_zaak_base_url")
    list_select_related = ("zaak", "_relevant_zaak", "_relevant_zaak_base_url")

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            relevant_zaak_url=Concat(
                F("_relevant_zaak_base_url__api_root"),
                F("_relevant_zaak_relative_url"),
                output_field=CharField(),
            )
        )


class ZaakBesluitForm(forms.ModelForm):
    class Meta:
        model = ZaakBesluit
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_besluit") and not cleaned_data.get(
            "_besluit_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een besluit opgeven: "
                "selecteer een besluit of vul een externe URL in."
            )

        return cleaned_data


@admin.register(ZaakBesluit)
class ZaakBesluitAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("zaak", "_besluit", "_besluit_base_url", "_besluit_relative_url")
    list_select_related = ("zaak", "_besluit", "_besluit_base_url")
    search_fields = (
        "uuid",
        "zaak__uuid",
        "zaak__identificatie",
        "_besluit__uuid",
        "_besluit__identificatie",
        "besluit_url",
    )
    form = ZaakBesluitForm
    ordering = ("zaak", "_besluit", "_besluit_base_url", "_besluit_relative_url")
    raw_id_fields = ("zaak", "_besluit", "_besluit_base_url")
    viewset = "openzaak.components.zaken.api.viewsets.ZaakBesluitViewSet"

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(
            besluit_url=Concat(
                F("_besluit_base_url__api_root"),
                F("_besluit_relative_url"),
                output_field=CharField(),
            )
        )


@admin.register(ZaakContactMoment)
class ZaakContactMomentAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "contactmoment"]
    list_select_related = ["zaak"]
    search_fields = (
        "uuid",
        "zaak__identificatie",
        "zaak__uuid",
        "contactmoment",
    )
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakContactMomentViewSet"


@admin.register(ZaakVerzoek)
class ZaakVerzoekAdmin(AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin):
    list_display = ["zaak", "verzoek"]
    list_select_related = ["zaak"]
    search_fields = (
        "uuid",
        "zaak__identificatie",
        "zaak__uuid",
        "verzoek",
    )
    raw_id_fields = ["zaak"]
    viewset = "openzaak.components.zaken.api.viewsets.ZaakVerzoekViewSet"


@admin.register(ZaakKenmerk)
class ZaakKenmerkAdmin(admin.ModelAdmin):
    list_display = ["zaak", "kenmerk", "bron"]
    list_select_related = ["zaak"]
    search_fields = ("zaak__identificatie", "zaak__uuid", "kenmerk", "bron")
    raw_id_fields = ["zaak"]


# inline classes for Zaak
class StatusInline(EditInlineAdminMixin, admin.TabularInline):
    model = Status
    fields = StatusAdmin.list_display
    fk_name = "zaak"


class ZaakObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakObject
    fields = ZaakObjectAdmin.list_display
    fk_name = "zaak"


class ZaakEigenschapInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakEigenschap
    fields = ZaakEigenschapAdmin.list_display
    fk_name = "zaak"


class ZaakInformatieObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakInformatieObject
    fields = ZaakInformatieObjectAdmin.list_display
    fk_name = "zaak"


class KlantContactInline(EditInlineAdminMixin, admin.TabularInline):
    model = KlantContact
    fields = KlantContactAdmin.list_display
    fk_name = "zaak"


class RolInline(EditInlineAdminMixin, admin.TabularInline):
    model = Rol
    fields = RolAdmin.list_display
    fk_name = "zaak"


class ResultaatInline(EditInlineAdminMixin, admin.TabularInline):
    model = Resultaat
    fields = ResultaatAdmin.list_display
    fk_name = "zaak"


class RelevanteZaakRelatieInline(EditInlineAdminMixin, admin.TabularInline):
    model = RelevanteZaakRelatie
    fields = RelevanteZaakRelatieAdmin.list_display
    fk_name = "zaak"


class ZaakBesluitInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakBesluit
    fields = ZaakBesluitAdmin.list_display
    fk_name = "zaak"


class ZaakContactMomentInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakContactMoment
    fields = ZaakContactMomentAdmin.list_display
    fk_name = "zaak"


class ZaakVerzoekInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakVerzoek
    fields = ZaakVerzoekAdmin.list_display
    fk_name = "zaak"


class ZaakKenmerkInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakKenmerk
    fields = ZaakKenmerkAdmin.list_display
    fk_name = "zaak"


class ZaakForm(forms.ModelForm):
    class Meta:
        model = Zaak
        fields = "__all__"
        exclude = ("_id", "_bronorganisatie", "_identificatie")  # legacy fields

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_zaaktype") and not cleaned_data.get(
            "_zaaktype_base_url"
        ):
            raise forms.ValidationError(
                "Je moet een zaaktype opgeven: "
                "selecteer een zaaktype of vul een externe URL in."
            )

        return cleaned_data


@admin.register(Zaak)
class ZaakAdmin(
    AuditTrailAdminMixin, ListObjectActionsAdminMixin, UUIDAdminMixin, OSMGeoAdmin
):
    list_display = (
        "identificatie",
        "get_zaaktype",
        "registratiedatum",
        "created_on",
        "startdatum",
        "einddatum",
        "get_status",
        "get_resultaat",
        "archiefstatus",
    )
    list_select_related = ("_zaaktype", "_zaaktype_base_url")
    search_fields = (
        "identificatie",
        "uuid",
        "zaaktype_url",
        "_zaaktype__identificatie",
        "_zaaktype__zaaktype_omschrijving",
        "rol__natuurlijkpersoon__inp_bsn",
        "rol__nietnatuurlijkpersoon__inn_nnp_id",
    )
    readonly_fields = ("created_on",)
    form = ZaakForm
    date_hierarchy = "registratiedatum"
    list_filter = ("startdatum", "archiefstatus", "vertrouwelijkheidaanduiding")
    ordering = ("-identificatie", "startdatum")
    inlines = [
        StatusInline,
        ZaakObjectInline,
        ZaakInformatieObjectInline,
        ZaakContactMomentInline,
        ZaakKenmerkInline,
        ZaakVerzoekInline,
        ZaakEigenschapInline,
        RolInline,
        ResultaatInline,
        RelevanteZaakRelatieInline,
        ZaakBesluitInline,
        KlantContactInline,
    ]
    raw_id_fields = ("_zaaktype", "hoofdzaak", "_zaaktype_base_url")
    viewset = "openzaak.components.zaken.api.viewsets.ZaakViewSet"
    widget = AuthorityAxisOrderOLWidget

    @admin.display(description="Zaaktype")
    def get_zaaktype(self, obj) -> str:
        if not obj._zaaktype:
            return ""

        return obj._zaaktype.identificatie

    @admin.display(description="Resultaat")
    def get_resultaat(self, obj) -> str:
        try:
            resultaat = obj.resultaat
            resultaattype = resultaat._resultaattype
            return resultaattype.omschrijving if resultaattype else ""
        except Resultaat.DoesNotExist:
            return ""

    @admin.display(description="Status")
    def get_status(self, obj) -> str:
        status = obj.current_status

        if not status or not status._statustype:
            return ""

        statustype = status._statustype
        return statustype.statustype_omschrijving

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(Status, obj),
            link_to_related_objects(Rol, obj),
            link_to_related_objects(ZaakEigenschap, obj),
            link_to_related_objects(Resultaat, obj),
            link_to_related_objects(ZaakObject, obj),
            link_to_related_objects(ZaakInformatieObject, obj),
            link_to_related_objects(KlantContact, obj),
            link_to_related_objects(ZaakKenmerk, obj),
            link_to_related_objects(ZaakBesluit, obj),
            link_to_related_objects(RelevanteZaakRelatie, obj, rel_field_name="zaak"),
        )

    def get_queryset(self, request):
        """
        annotate queryset with composite url field for search purposes
        """
        queryset = super().get_queryset(request)

        status_prefetch = Prefetch(
            "status_set",
            queryset=(
                Status.objects.select_related("_statustype")
                .filter(_statustype__isnull=False)
                .order_by("-datum_status_gezet")
            ),
        )

        resultaat_prefetch = Prefetch(
            "resultaat",
            queryset=(
                Resultaat.objects.select_related("_resultaattype").filter(
                    _resultaattype__isnull=False
                )
            ),
        )

        return (
            queryset.select_related("_zaaktype")
            .prefetch_related(resultaat_prefetch, status_prefetch)
            .annotate(
                zaaktype_url=Concat(
                    F("_zaaktype_base_url__api_root"),
                    F("_zaaktype_relative_url"),
                    output_field=CharField(),
                )
            )
        )
