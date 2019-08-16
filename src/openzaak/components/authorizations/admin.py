from django.contrib import admin

from .models import Applicatie, Autorisatie


@admin.register(Autorisatie)
class AutorisatieAdmin(admin.ModelAdmin):
    list_display = ('applicatie', 'component', 'zaaktype', 'scopes', 'max_vertrouwelijkheidaanduiding')


class AutorisatieInline(admin.TabularInline):
    model = Autorisatie


@admin.register(Applicatie)
class ApplicatieAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'client_ids', 'label', 'heeft_alle_autorisaties', )
    readonly_fields = ('uuid',)
    inlines = (AutorisatieInline,)
