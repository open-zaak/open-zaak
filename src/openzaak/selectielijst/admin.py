from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import ReferentieLijstConfig


@admin.register(ReferentieLijstConfig)
class ReferentieLijstConfigAdmin(SingletonModelAdmin):
    list_display = ["api_root"]
