from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.template import Library

register = Library()


@register.filter
def boolean_icon(field_val):
    return _boolean_icon(field_val)
