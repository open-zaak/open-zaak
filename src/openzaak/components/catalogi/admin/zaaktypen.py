# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging

from django.apps import apps
from django.contrib import admin, messages
from django.db.models import Field
from django.forms import ChoiceField
from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _

from openzaak.selectielijst.admin_fields import (
    get_processtype_readonly_field,
    get_procestype_field,
)
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..models import (
    Eigenschap,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypenRelatie,
)
from .eigenschap import EigenschapAdmin
from .forms import ZaakTypeForm
from .mixins import (
    CatalogusContextAdminMixin,
    ExportMixin,
    NewVersionMixin,
    PublishAdminMixin,
    ReadOnlyPublishedMixin,
    ReadOnlyPublishedZaaktypeMixin,
)
from .resultaattype import ResultaatTypeAdmin
from .roltype import RolTypeAdmin
from .statustype import StatusTypeAdmin

logger = logging.getLogger(__name__)


@admin.register(ZaakTypenRelatie)
class ZaakTypenRelatieAdmin(ReadOnlyPublishedZaaktypeMixin, admin.ModelAdmin):
    model = ZaakTypenRelatie

    # List
    list_display = ("gerelateerd_zaaktype", "zaaktype")
    list_filter = ("zaaktype", "aard_relatie")
    ordering = ("zaaktype", "gerelateerd_zaaktype")
    search_fields = ("gerelateerd_zaaktype", "toelichting", "zaaktype__uuid")

    # Detail
    fieldsets = (
        (
            _("Algemeen"),
            {"fields": ("gerelateerd_zaaktype", "aard_relatie", "toelichting")},
        ),
        (_("Relaties"), {"fields": ("zaaktype",)},),
    )
    raw_id_fields = ("zaaktype",)


class StatusTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = StatusType
    fields = StatusTypeAdmin.list_display
    fk_name = "zaaktype"


class RolTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = RolType
    fields = RolTypeAdmin.list_display
    fk_name = "zaaktype"


class EigenschapInline(EditInlineAdminMixin, admin.TabularInline):
    model = Eigenschap
    fields = EigenschapAdmin.list_display
    fk_name = "zaaktype"


class ResultaatTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ResultaatType
    fields = ResultaatTypeAdmin.list_display
    fk_name = "zaaktype"


class ZaakTypenRelatieInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakTypenRelatie
    fk_name = "zaaktype"
    fields = ZaakTypenRelatieAdmin.list_display


@admin.register(ZaakType)
class ZaakTypeAdmin(
    ReadOnlyPublishedMixin,
    NewVersionMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    PublishAdminMixin,
    ExportMixin,
    DynamicArrayMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = ZaakType
    form = ZaakTypeForm

    # List
    list_display = (
        "zaaktype_omschrijving",
        "identificatie",
        "versiedatum",
        "is_published",
    )
    list_filter = (
        "catalogus",
        "publicatie_indicatie",
        "verlenging_mogelijk",
        "opschorting_en_aanhouding_mogelijk",
        "indicatie_intern_of_extern",
        "vertrouwelijkheidaanduiding",
    )
    ordering = ("catalogus", "identificatie")
    search_fields = (
        "uuid",
        "identificatie",
        "zaaktype_omschrijving",
        "zaaktype_omschrijving_generiek",
        "doel",
        "aanleiding",
        "onderwerp",
        "toelichting",
    )
    date_hierarchy = "versiedatum"

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "identificatie",
                    "uuid",
                    "zaaktype_omschrijving",
                    "zaaktype_omschrijving_generiek",
                    "doel",
                    "aanleiding",
                    "toelichting",
                    "indicatie_intern_of_extern",
                    "trefwoorden",
                    "vertrouwelijkheidaanduiding",
                    "producten_of_diensten",
                    "verantwoordingsrelatie",
                )
            },
        ),
        (
            _("Behandeling"),
            {
                "fields": (
                    "handeling_initiator",
                    "onderwerp",
                    "handeling_behandelaar",
                    "doorlooptijd_behandeling",
                    "servicenorm_behandeling",
                ),
            },
        ),
        (
            _("Opschorten/verlengen"),
            {
                "fields": (
                    "opschorting_en_aanhouding_mogelijk",
                    "verlenging_mogelijk",
                    "verlengingstermijn",
                )
            },
        ),
        (
            _("Gemeentelijke selectielijst"),
            {"fields": ("selectielijst_procestype_jaar", "selectielijst_procestype",)},
        ),
        (
            _("Referentieproces"),
            {"fields": ("referentieproces_naam", "referentieproces_link")},
        ),
        (_("Publicatie"), {"fields": ("publicatie_indicatie", "publicatietekst")}),
        (_("Relaties"), {"fields": ("catalogus", "deelzaaktypen")}),
        (
            _("Geldigheid"),
            {
                "fields": (
                    "versiedatum",
                    "datum_begin_geldigheid",
                    "datum_einde_geldigheid",
                )
            },
        ),
    )
    raw_id_fields = ("catalogus", "deelzaaktypen")
    readonly_fields = ("versiedatum",)
    inlines = (
        ZaakTypenRelatieInline,
        StatusTypeInline,
        RolTypeInline,
        EigenschapInline,
        ResultaatTypeInline,
    )
    change_form_template = "admin/catalogi/change_form_zaaktype.html"
    exclude_copy_relation = ("zaak",)

    # For export mixin
    resource_name = "zaaktype"

    def get_related_objects(self, obj):
        resources = {}

        resources["ZaakType"] = [obj.pk]

        # M2M relations
        resources["BesluitType"] = list(obj.besluittypen.values_list("pk", flat=True))
        resources["InformatieObjectType"] = list(
            obj.informatieobjecttypen.values_list("pk", flat=True)
        )

        resources["ZaakTypeInformatieObjectType"] = list(
            obj.zaaktypeinformatieobjecttype_set.values_list("pk", flat=True)
        )

        # Resources with foreign keys to ZaakType
        fields = ["ResultaatType", "RolType", "StatusType", "Eigenschap"]
        for field in fields:
            model = apps.get_model("catalogi", field)
            resources[field] = list(
                model.objects.filter(zaaktype=obj).values_list("pk", flat=True)
            )

        resource_list = []
        id_list = []
        for resource, ids in resources.items():
            if ids:
                resource_list.append(resource)
                id_list.append(ids)

        return resource_list, id_list

    def _publish_validation_errors(self, obj):
        errors = []
        if (
            obj.besluittypen.filter(concept=True).exists()
            or obj.informatieobjecttypen.filter(concept=True).exists()
        ):
            errors.append(_("All related resources should be published"))
        return errors

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(StatusType, obj),
            link_to_related_objects(RolType, obj),
            link_to_related_objects(Eigenschap, obj),
            link_to_related_objects(ResultaatType, obj),
            link_to_related_objects(ZaakTypenRelatie, obj),
        )

    def formfield_for_dbfield(self, db_field: Field, request: HttpRequest, **kwargs):
        if db_field.name == "selectielijst_procestype_jaar":
            referentielijst_config = ReferentieLijstConfig.get_solo()
            choices = [
                (year, str(year)) for year in referentielijst_config.allowed_years
            ]
            return ChoiceField(
                label=db_field.verbose_name.capitalize(),
                choices=choices,
                initial=referentielijst_config.default_year,
                required=False,
                help_text=db_field.help_text,
                localize=False,
            )
        if db_field.name == "selectielijst_procestype":
            if "object_id" in request.resolver_match.kwargs:
                obj = ZaakType.objects.get(
                    id=str(request.resolver_match.kwargs["object_id"])
                )
                procestype_jaar = obj.selectielijst_procestype_jaar
            else:
                referentielijst_config = ReferentieLijstConfig.get_solo()
                procestype_jaar = referentielijst_config.default_year
            try:
                return get_procestype_field(
                    db_field, request, procestype_jaar, **kwargs
                )
            except AttributeError as e:
                logger.exception(e)

                msg = _(
                    "Something went wrong while fetching procestypen, "
                    "this could be due to an incorrect Selectielijst configuration."
                )
                messages.add_message(
                    request, messages.ERROR, msg, extra_tags="procestypen"
                )

                kwargs["initial"] = _("Selectielijst configuration must be fixed first")
                kwargs["disabled"] = True

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.versiedatum = obj.datum_begin_geldigheid

        super().save_model(request, obj, form, change)

    def render_readonly(self, field, result_repr, value):
        if field.name == "selectielijst_procestype" and value:
            res = get_processtype_readonly_field(value)
            return res

        return super().render_readonly(field, result_repr, value)
