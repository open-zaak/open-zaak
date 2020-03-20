from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import InternalService, NLXConfig


@admin.register(NLXConfig)
class NLXConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(InternalService)
class InternalServiceAdmin(admin.ModelAdmin):
    list_display = ("api_type", "enabled", "nlx")
