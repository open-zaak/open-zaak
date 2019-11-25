import uuid
from datetime import date
from urllib.parse import quote as urlquote

from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
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
    def _publish_validation_errors(self, obj):
        return []

    def response_post_save_change(self, request, obj):
        if "_publish" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            errors = self._publish_validation_errors(obj)
            if errors:
                for error in errors:
                    self.message_user(request, error, level=messages.ERROR)
            else:
                obj.concept = False
                obj.save()
                msg = _("The resource has been published successfully!")
                self.message_user(request, msg, level=messages.SUCCESS)

            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)


class NewVersionMixin(object):
    exclude_copy_relation = []

    def create_new_version(self, obj):
        old_pk = obj.pk

        # new obj
        version_date = date.today()

        obj.pk = None
        obj.uuid = uuid.uuid4()
        obj.datum_begin_geldigheid = version_date
        obj.versiedatum = version_date
        obj.datum_einde_geldigheid = None
        obj.save()

        related_objects = [
            f
            for f in obj._meta.get_fields(include_hidden=True)
            if (f.auto_created and not f.concrete)
        ]

        # related objects
        for relation in related_objects:
            if relation.name in self.exclude_copy_relation:
                continue

            # m2m relation included in the loop below as one_to_many
            if relation.one_to_many or relation.one_to_one:
                remote_model = relation.related_model
                remote_field = relation.field.name

                related_queryset = remote_model.objects.filter(**{remote_field: old_pk})
                for related_obj in related_queryset:
                    related_obj.pk = None
                    setattr(related_obj, remote_field, obj)

                    if hasattr(related_obj, "uuid"):
                        related_obj.uuid = uuid.uuid4()
                    related_obj.save()

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        msg_dict = {
            "name": opts.verbose_name,
            "obj": format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_addversion" in request.POST:
            self.create_new_version(obj)

            msg = format_html(
                _('The new version of {name} "{obj}" was successfully created'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)

            redirect_url = reverse(
                "admin:%s_%s_change" % (opts.app_label, opts.model_name),
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts}, redirect_url
            )
            return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)
