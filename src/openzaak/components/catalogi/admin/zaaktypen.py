from datetime import date
import uuid
from urllib.parse import quote as urlquote

from django.contrib import admin, messages
from django.db.models import Field
from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from openzaak.selectielijst.admin import get_procestype_field
from openzaak.utils.admin import (
    DynamicArrayMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
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
from .mixins import GeldigheidAdminMixin, PublishAdminMixin
from .resultaattype import ResultaatTypeAdmin
from .roltype import RolTypeAdmin
from .statustype import StatusTypeAdmin


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


class ZaakTypenRelatieInline(admin.TabularInline):
    model = ZaakTypenRelatie
    fk_name = "zaaktype"
    extra = 1


@admin.register(ZaakType)
class ZaakTypeAdmin(
    ListObjectActionsAdminMixin,
    GeldigheidAdminMixin,
    PublishAdminMixin,
    DynamicArrayMixin,
    admin.ModelAdmin,
):
    model = ZaakType
    form = ZaakTypeForm

    # List
    list_display = (
        "identificatie",
        "zaaktype_omschrijving",
        "catalogus",
        "uuid",
        "get_absolute_api_url",
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
        "identificatie",
        "zaaktype_omschrijving",
        "zaaktype_omschrijving_generiek",
        "zaakcategorie",
        "doel",
        "aanleiding",
        "onderwerp",
        "toelichting",
    )

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "identificatie",
                    "zaaktype_omschrijving",
                    "zaaktype_omschrijving_generiek",
                    "doel",
                    "aanleiding",
                    "toelichting",
                    "indicatie_intern_of_extern",
                    "handeling_initiator",
                    "onderwerp",
                    "handeling_behandelaar",
                    "doorlooptijd_behandeling",
                    "servicenorm_behandeling",
                    "opschorting_en_aanhouding_mogelijk",
                    "verlenging_mogelijk",
                    "verlengingstermijn",
                    "trefwoorden",
                    "vertrouwelijkheidaanduiding",
                    "producten_of_diensten",
                    "verantwoordingsrelatie",
                )
            },
        ),
        (_("Gemeentelijke selectielijst"), {"fields": ("selectielijst_procestype",)}),
        (
            _("Referentieproces"),
            {"fields": ("referentieproces_naam", "referentieproces_link")},
        ),
        (_("Publicatie"), {"fields": ("publicatie_indicatie", "publicatietekst")}),
        (_("Relaties"), {"fields": ("catalogus",)}),
        (_("Geldigheid"), {"fields": ("versiedatum", "datum_begin_geldigheid", "datum_einde_geldigheid")}),
    )
    raw_id_fields = ("catalogus",)
    readonly_fields = ("versiedatum", )
    inlines = (
        ZaakTypenRelatieInline,
        StatusTypeInline,
        RolTypeInline,
        EigenschapInline,
        ResultaatTypeInline,
    )

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
        )

    def formfield_for_dbfield(self, db_field: Field, request: HttpRequest, **kwargs):
        if db_field.name == "selectielijst_procestype":
            return get_procestype_field(db_field, request, **kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.versiedatum = obj.datum_begin_geldigheid

        super().save_model(request, obj, form, change)

    def create_new_version(self, obj):
        old_pk = obj.pk

        # TODO add validation for end date
        # FIXME need obj.save() ????

        # new obj
        version_date = date.today()

        obj.pk = None
        obj.uuid = uuid.uuid4()
        obj.datum_begin_geldigheid = version_date
        obj.versiedatum = version_date
        obj.datum_einde_geldigheid = None
        obj.save()

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_addVersion" in request.POST:
            self.create_new_version(obj)

            msg = format_html(
                _('The new version of {name} "{obj}" was successfully created'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)

            redirect_url = reverse('admin:%s_%s_change' %
                                   (opts.app_label, opts.model_name),
                                   args=(obj.pk,),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)
