from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models import CheckListItem, StatusType
from .mixins import FilterSearchOrderingAdminMixin


@admin.register(CheckListItem)
class CheckListItemAdmin(admin.ModelAdmin):
    list_display = ('itemnaam',)
    fields = ('itemnaam', 'vraagstelling', 'verplicht', 'toelichting')


@admin.register(StatusType)
class StatusTypeAdmin(FilterSearchOrderingAdminMixin, admin.ModelAdmin):
    model = StatusType

    # List
    list_display = ('statustype_omschrijving', 'statustypevolgnummer', 'zaaktype')

    # Details
    fieldsets = (
        (_('Algemeen'), {
            'fields': (
                'statustype_omschrijving',
                'statustype_omschrijving_generiek',
                'statustypevolgnummer',
                'doorlooptijd_status',
                'informeren',
                'statustekst',
                'toelichting',
            )
        }),
        (_('Relaties'), {
            'fields': (
                'zaaktype',
                'checklistitem',
                'roltypen',
            )
        }),
    )
    filter_horizontal = (
        'roltypen',
        'checklistitem',
    )
    raw_id_fields = ('zaaktype', )
