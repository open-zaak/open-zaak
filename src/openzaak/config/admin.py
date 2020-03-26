from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import NLXConfig


@admin.register(NLXConfig)
class NLXConfigAdmin(SingletonModelAdmin):
    pass
