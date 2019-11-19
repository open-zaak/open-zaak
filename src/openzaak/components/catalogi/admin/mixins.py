from django.contrib import messages
from django.http import HttpResponseRedirect
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


class ConceptAdminMixin(object):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + ((_("Concept"), {"fields": ("concept",)}),)


class PublishAdminMixin:
    def response_post_save_change(self, request, obj):
        if "_publish" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            obj.concept = False
            obj.save()
            msg = _("The resource has been published successfully!")
            self.message_user(request, msg, level=messages.SUCCESS)

            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)
