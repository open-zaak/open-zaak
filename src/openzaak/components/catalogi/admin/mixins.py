import os
import uuid
from datetime import date
from urllib.parse import quote as urlquote

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.management import CommandError, call_command
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models import ZaakTypeInformatieObjectType
from .forms import CatalogusImportForm


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
        obj.concept = True
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
                **msg_dict,
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


class CatalogusImportExportMixin:
    def import_view(self, request):
        form = CatalogusImportForm(request.POST, request.FILES)
        context = dict(self.admin_site.each_context(request), form=form)
        if "_import" in request.POST:
            if form.is_valid():
                try:
                    import_file = form.cleaned_data["file"]
                    call_command(
                        "import", import_file_content=import_file.read()
                    )
                    self.message_user(
                        request,
                        _("Catalogus successfully imported"),
                        level=messages.SUCCESS,
                    )
                    return HttpResponseRedirect(
                        reverse("admin:catalogi_catalogus_changelist")
                    )
                except CommandError as exc:
                    self.message_user(request, exc, level=messages.ERROR)
        return TemplateResponse(
            request, "admin/catalogi/import_catalogus.html", context
        )

    def get_related_objects(self, obj):
        resources = {}

        resources["Catalogus"] = [obj.pk]

        # Resources with foreign keys to catalogus
        fields = ["InformatieObjectType", "BesluitType", "ZaakType"]
        for field in fields:
            resources[field] = list(
                getattr(obj, f"{field.lower()}_set").values_list("pk", flat=True)
            )
        resources["ZaakTypeInformatieObjectType"] = list(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype__in=resources["ZaakType"],
                informatieobjecttype__in=resources["InformatieObjectType"],
            ).values_list("pk", flat=True)
        )

        # Resources with foreign keys to  ZaakType
        fields = ["ResultaatType", "RolType", "StatusType", "Eigenschap"]
        for field in fields:
            model = apps.get_model("catalogi", field)
            resources[field] = list(
                model.objects.filter(zaaktype__in=resources["ZaakType"]).values_list(
                    "pk", flat=True
                )
            )

        resource_list = []
        id_list = []
        for resource, ids in resources.items():
            if ids:
                resource_list.append(resource)
                id_list.append(ids)

        return resource_list, id_list

    def response_post_save_change(self, request, obj):
        if "_export" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            resource_list, id_list = self.get_related_objects(obj)

            response = HttpResponse(content_type="application/zip")
            response["Content-Disposition"] = "attachment;filename={}".format(
                f"{obj.domein}.zip"
            )
            call_command("export", response=response, resource=resource_list, ids=id_list,)

            response["Content-Length"] = len(response.content)

            self.message_user(
                request,
                _("Catalogus {} was successfully exported").format(obj),
                level=messages.SUCCESS,
            )
            return response
        else:
            return super().response_post_save_change(request, obj)
