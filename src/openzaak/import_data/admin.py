from django.contrib import admin

from openzaak.import_data.models import Import


@admin.register(Import)
class ImportAdmin(admin.ModelAdmin):
    model = Import
