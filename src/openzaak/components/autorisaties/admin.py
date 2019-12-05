from django.contrib import admin
from django.forms import BaseModelFormSet
from django.urls import path

from vng_api_common.authorizations.models import (
    Applicatie,
    AuthorizationsConfig,
    Autorisatie,
)
from vng_api_common.models import JWTSecret

from .admin_views import AutorisatiesView
from .forms import ApplicatieForm, CredentialsFormSet

admin.site.unregister(AuthorizationsConfig)
admin.site.unregister(Applicatie)


class AutorisatieInline(admin.TabularInline):
    model = Autorisatie
    extra = 0
    fields = ["component", "scopes", "get_foo"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def get_foo(self, obj) -> str:
        return "foo"


class CredentialsInline(admin.TabularInline):
    model = JWTSecret
    formset = BaseModelFormSet
    fields = ("identifier", "secret")
    extra = 1

    # Disable system checks, since this model is not related at all to Applicatie
    def check(self, *args, **kwargs):
        return []

    def get_formset(self, request, obj=None, **kwargs):
        return CredentialsFormSet


@admin.register(Applicatie)
class ApplicatieAdmin(admin.ModelAdmin):
    list_display = ("uuid", "client_ids", "label", "heeft_alle_autorisaties")
    readonly_fields = ("uuid",)
    form = ApplicatieForm
    inlines = (
        CredentialsInline,
        AutorisatieInline,
    )

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/autorisaties/",
                self.admin_site.admin_view(self.autorisaties_view),
                name="authorizations_applicatie_autorisaties",
            ),
        ]
        return custom_urls + urls

    @property
    def autorisaties_view(self):
        return AutorisatiesView.as_view(admin_site=self.admin_site, model_admin=self,)
