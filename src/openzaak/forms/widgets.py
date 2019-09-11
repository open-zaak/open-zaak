from django import forms
from django.utils.translation import ugettext_lazy as _

from dateutil.relativedelta import relativedelta
from relativedeltafield import format_relativedelta


class BooleanRadio(forms.RadioSelect):
    def __init__(self, attrs=None):
        choices = ((True, _("Yes")), (False, _("No")))
        super().__init__(attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, False)
        return {True: True, "True": True, "False": False, False: False}[value]


# TODO: should live in vng-api-common
class RelativeDeltaWidget(forms.TextInput):
    def format_value(self, value):
        if isinstance(value, relativedelta):
            return format_relativedelta(value)
        return super().format_value(value)
