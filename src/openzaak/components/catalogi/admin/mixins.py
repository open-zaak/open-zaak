# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from copy import deepcopy
from urllib.parse import parse_qsl, quote as urlquote

from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import flatten_fieldsets
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import CommandError, call_command
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _, ngettext_lazy

from dateutil.relativedelta import relativedelta

from openzaak.components.catalogi.utils import has_overlapping_objects
from openzaak.utils.admin import ExtraContextAdminMixin

from ..api.viewsets import (
    BesluitTypeViewSet,
    InformatieObjectTypeViewSet,
    ZaakTypeViewSet,
)
from ..models import BesluitType, Catalogus, InformatieObjectType, ZaakType
from .forms import CatalogusImportForm
from .helpers import AdminForm
from .side_effects import NotificationSideEffect, VersioningSideEffect

VIEWSET_FOR_MODEL = {
    ZaakType: ZaakTypeViewSet,
    InformatieObjectType: InformatieObjectTypeViewSet,
    BesluitType: BesluitTypeViewSet,
}


class GeldigheidAdminMixin:
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return tuple(fieldsets) + (
            (
                _("Geldigheid"),
                {"fields": ("datum_begin_geldigheid", "datum_einde_geldigheid")},
            ),
        )


class ConceptAdminMixin:
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

                redirect_url = request.path
                redirect_url = add_preserved_filters(
                    {
                        "preserved_filters": self.get_preserved_filters(request),
                        "opts": self.opts,
                    },
                    redirect_url,
                )
                return HttpResponseRedirect(redirect_url)

            obj.publish()
            msg = _("The resource has been published successfully!")
            self.message_user(request, msg, level=messages.SUCCESS)

            return HttpResponseRedirect(request.path)
        else:
            return super().response_post_save_change(request, obj)

    @admin.action(description=_("Publish selected %(verbose_name_plural)s"))
    def publish_selected(self, request, queryset):
        published = 0
        already_published = queryset.filter(concept=False).count()

        if already_published:
            msg = (
                ngettext_lazy(
                    "%d object is already published",
                    "%d objects are already published",
                    already_published,
                )
                % already_published
            )
            self.message_user(request, msg, level=messages.WARNING)

        for obj in queryset.filter(concept=True):
            errors = self._publish_validation_errors(obj)
            if errors:
                for error in errors:
                    msg = _("%(obj)s can't be published: %(error)s") % {
                        "obj": obj,
                        "error": error,
                    }
                    self.message_user(request, msg, level=messages.ERROR)
            else:
                try:
                    obj.publish()
                    published += 1
                except ValidationError as e:
                    obj.concept = True  # change to true so __str__ shows (CONCEPT)
                    msg = _("%(obj)s can't be published: %(error)s") % {
                        "obj": obj,
                        "error": e.message,
                    }
                    self.message_user(request, msg, level=messages.ERROR)

        if published:
            msg = (
                ngettext_lazy(
                    "%d object has been published successfully",
                    "%d objects have been published successfully",
                    published,
                )
                % published
            )
            self.message_user(request, msg, level=messages.SUCCESS)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions["publish_selected"] = self.get_action("publish_selected")
        return actions


class GeldigheidPublishAdminMixin(PublishAdminMixin):
    def _publish_validation_errors(self, obj):

        if has_overlapping_objects(
            model_manager=obj._meta.default_manager,
            catalogus=obj.catalogus,
            omschrijving_query={
                obj.omschrijving_field: getattr(obj, obj.omschrijving_field)
            },
            begin_geldigheid=obj.datum_begin_geldigheid,
            einde_geldigheid=obj.datum_einde_geldigheid,
            instance=obj,
            concept=False,
        ):
            return [
                f"{obj._meta.verbose_name} versies (dezelfde omschrijving) mogen geen "
                "overlappende geldigheid hebben."
            ]

        return []


class SideEffectsMixin:
    """
    Invoke handlers that depend on an object being saved in the admin.

    An object can either be created or updated from the admin. This mixin merely holds
    a reference to various loosely coupled handlers that introduce side effects from
    the action of saving the main object.

    Note that the django admin ``change_view`` method runs in an atomic transaction,
    so any side effects should take this into account.

    Also note that we tap into the ``save_related`` method, because this method gives
    us the most context while ensuring the main object procesisng has been done.
    """

    exclude_copy_relation = []

    def save_related(self, request, form, formsets, change):
        original = deepcopy(form.instance)
        # we set up our custom handlers and processing
        # since know we are using model forms, we can mutate form.instance for further
        # calls, which is a bit of a nasty hack, but necessary since the admin instance
        # is not thread safe
        with VersioningSideEffect(
            self,
            request,
            original=original,
            change=change,
            form=form,
        ) as side_effect:
            super().save_related(request, form, formsets, change)

        # we essentially "replace" the original object with the new version. In
        # ``response_change``, the redirect to the new version should happen, which
        # we do by overwriting the PK
        if side_effect.new_version is not None:
            form.instance.pk = side_effect.new_version.pk

        notification_side_effect = NotificationSideEffect(
            self,
            request,
            original=side_effect.new_version
            or original,  # use the new version if it exists
            change=change,
            form=form,
        )
        notification_side_effect.apply()

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)
        msg_dict = {
            "name": opts.verbose_name,
            "obj": format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        # because of the VersioningSideEffect, the form.instance has been mutated
        # with the newly created object, so we can generate the right redirect link
        if "_addversion" in request.POST:
            msg = format_html(
                _('The new version of {name} "{obj}" was successfully created'),
                **msg_dict,
            )
            self.message_user(request, msg, messages.SUCCESS)

            redirect_url = reverse(
                "admin:{}_{}_change".format(opts.app_label, opts.model_name),
                args=(obj.pk,),
                current_app=self.admin_site.name,
            )
            redirect_url = add_preserved_filters(
                {"preserved_filters": preserved_filters, "opts": opts}, redirect_url
            )
            return HttpResponseRedirect(redirect_url)

        return super().response_change(request, obj)


class ExportMixin:
    resource_name = ""

    def get_related_objects(self, obj):
        """
        Must be implemented to retrieve the objects that have to be exported
        along with the main object
        """
        return [], []

    def response_post_save_change(self, request, obj):
        if "_export" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            resource_list, id_list = self.get_related_objects(obj)

            response = HttpResponse(content_type="application/zip")
            filename = slugify(str(obj))
            response["Content-Disposition"] = "attachment;filename={}".format(
                f"{filename}.zip"
            )
            call_command(
                "export",
                response=response,
                resource=resource_list,
                ids=id_list,
            )

            response["Content-Length"] = len(response.content)

            self.message_user(
                request,
                _("{} {} was successfully exported").format(
                    self.resource_name.capitalize(), obj
                ),
                level=messages.SUCCESS,
            )
            return response
        else:
            return super().response_post_save_change(request, obj)


class CatalogusContextAdminMixin(ExtraContextAdminMixin):
    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)

        zaaktype = None
        iotype = None
        catalogus = None

        _changelist_filters = dict(parse_qsl(request.GET.get("_changelist_filters")))
        zaaktype_pk = _changelist_filters.get(
            "zaaktype__id__exact", request.GET.get("zaaktype__id__exact")
        )
        iotype_pk = _changelist_filters.get(
            "informatieobjecttype__id__exact",
            request.GET.get("informatieobjecttype__id__exact"),
        )
        catalogus_pk = _changelist_filters.get(
            "catalogus__id__exact", request.GET.get("catalogus__id__exact")
        )

        if zaaktype_pk:
            zaaktype = (
                ZaakType.objects.select_related("catalogus")
                .filter(pk=int(zaaktype_pk))
                .first()
            )
            catalogus = zaaktype.catalogus
        elif iotype_pk:
            iotype = (
                InformatieObjectType.objects.select_related("catalogus")
                .filter(pk=int(iotype_pk))
                .first()
            )
            catalogus = iotype.catalogus
        elif catalogus_pk:
            catalogus = Catalogus.objects.get(pk=int(catalogus_pk))

        context.update(
            {
                "zaaktype": zaaktype,
                "informatieobjecttype": iotype,
                "catalogus": catalogus,
            }
        )

        return context


class ImportMixin:
    resource_name = ""

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name=f"catalogi_{self.resource_name}_import",
            )
        ]
        return my_urls + urls

    def import_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        form = CatalogusImportForm(request.POST, request.FILES)
        context = dict(self.admin_site.each_context(request), form=form)
        if "_import" in request.POST:
            form = CatalogusImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    import_file = form.cleaned_data["file"]
                    generate_new_uuids = form.cleaned_data["generate_new_uuids"]
                    call_command(
                        "import",
                        import_file_content=import_file.read(),
                        generate_new_uuids=generate_new_uuids,
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
        else:
            form = CatalogusImportForm()

        context = dict(self.admin_site.each_context(request), form=form)

        return TemplateResponse(
            request, "admin/catalogi/import_catalogus.html", context
        )


class ReadOnlyPublishedBaseMixin:
    def get_concept(self, obj):
        return NotImplementedError(
            "subclasses of ReadOnlyPublishedBaseMixin must provide a get_concept() method"
        )

    def has_delete_permission(self, request, obj=None):
        if self.get_concept(obj):
            return super().has_delete_permission(request, obj)
        return False

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)

        if self.get_concept(obj):
            return inlines

        for inline in inlines:
            inline.show_change_link = False
            inline.show_add_link = False

        return inlines

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        # change form class in context
        adminform = context["adminform"]
        context["adminform"] = AdminForm(
            self.render_readonly,
            adminform.form,
            list(self.get_fieldsets(request, obj)),
            (
                self.get_prepopulated_fields(request, obj)
                if add or self.has_change_permission(request, obj)
                else {}
            ),
            adminform.readonly_fields,
            model_admin=self,
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    def render_readonly(self, field, result_repr, value):
        if isinstance(value, relativedelta) and not value:
            return self.get_empty_value_display()

        # override method to customize formatting
        return result_repr


class ReadOnlyPublishedMixin(ReadOnlyPublishedBaseMixin):
    def get_concept(self, obj):
        if not obj:
            return True
        return obj.concept

    def get_readonly_fields(self, request, obj=None):
        if self.get_concept(obj):
            return super().get_readonly_fields(request, obj)

        # leave datum_einde_geldigheid editable
        field_names = [field.name for field in obj._meta.get_fields()]
        if "datum_einde_geldigheid" in field_names:
            field_names.remove("datum_einde_geldigheid")
        return field_names


class ReadOnlyPublishedParentMixin(ReadOnlyPublishedBaseMixin):
    def has_change_permission(self, request, obj=None):
        if self.get_concept(obj):
            return super().has_change_permission(request, obj)

        if request.method == "GET":
            return False

        # If the new ZaakType is published and the form is valid, the user should have
        # read-only access. If the new ZaakType is published and the form is invalid,
        # the permissions for the old ZaakType apply
        fieldsets = self.get_fieldsets(request, obj)
        ModelForm = self.get_form(
            request, obj, change=False, fields=flatten_fieldsets(fieldsets)
        )
        form_validated = ModelForm(request.POST, request.FILES, instance=obj).is_valid()
        if form_validated:
            return False
        return self.get_concept(self.model.objects.get(id=obj.id))


class ReadOnlyPublishedZaaktypeMixin(ReadOnlyPublishedParentMixin):
    def get_concept(self, obj):
        if not obj:
            return True
        return obj.zaaktype.concept
