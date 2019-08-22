from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _


class GeldigheidAdminMixin(object):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + (
            (
                _("Geldigheid"),
                {"fields": ("datum_begin_geldigheid", "datum_einde_geldigheid")},
            ),
        )

    #
    # formfield_overrides = {
    #     StUFDateField: {'widget': AdminDateWidget},
    # }


class FilterSearchOrderingAdminMixin(object):
    """
    Consult the model options to set filters and search fields.
    """

    def __init__(self, *args, **kwargs):
        if not hasattr(self, "model"):
            raise ImproperlyConfigured(
                'The "model" attribute needs to be set on "{}" if "{}" is used.'.format(
                    self.__class__.__name__, "FilterSearchOrderingAdminMixin"
                )
            )

        super().__init__(*args, **kwargs)

    def get_model_option(self, attr, default=None):
        if default is None:
            default = []
        return getattr(self.model._meta, attr, default)

    def get_list_filter(self, request):
        """
        The fields that can be filtered on in the API, are shown as filter in the admin.
        """
        return self.get_model_option("filter_fields", super().get_list_filter(request))

    def get_search_fields(self, request):
        """
        The fields that are searched in the admin.
        """
        return self.get_model_option(
            "search_fields", super().get_search_fields(request)
        )


class ConceptAdminMixin(object):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + ((_("Concept"), {"fields": ("concept",)}),)
