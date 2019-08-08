from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import RolType
from .mixins import FilterSearchOrderingAdminMixin


@admin.register(RolType)
class RolTypeAdmin(FilterSearchOrderingAdminMixin, admin.ModelAdmin):
    model = RolType

    # List
    list_display = ('omschrijving', 'zaaktype', 'uuid')

    # Details
    fieldsets = (
        (_('Algemeen'), {
            'fields': (
                'omschrijving',
                'omschrijving_generiek',
                'soort_betrokkene',
            )
        }),
        (_('Relaties'), {
            'fields': (
                'zaaktype',
            )
        }),
    )
    raw_id_fields = ('zaaktype', )
