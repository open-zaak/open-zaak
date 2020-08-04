# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Optional, Tuple
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.db.models.base import Model, ModelBase
from django.urls import reverse
from django.utils.html import format_html
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from rest_framework.settings import api_settings
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import CommonResourceAction


def link_to_related_objects(
    model: ModelBase, obj: Model, rel_field_name: Optional[str] = None
) -> Tuple[str, str]:
    """
    Link to the admin list of ``model`` objects related to ``obj``.

    Introspects the model field relations so that the filter query params can
    be automatically derived and kept in sync when field names change.
    """
    main_model = obj._meta.model
    if not rel_field_name:
        relation_fields = [
            field
            for field in model._meta.get_fields()
            if getattr(field, "related_model", None) is main_model
        ]
        # TODO: if multiple relations to the same model happen, we need to explicitly
        # pass the field name
        assert len(relation_fields) == 1
        relation_field = relation_fields[0]
    else:
        relation_field = model._meta.get_field(rel_field_name)

    query = {f"{relation_field.name}__id__exact": obj.pk}
    view_name = f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
    changelist_url = f"{reverse(view_name)}?{urlencode(query)}"
    return (
        _("Toon {verbose_name}").format(verbose_name=model._meta.verbose_name_plural),
        changelist_url,
    )


class ObjectActionsAdminMixin(object):
    def _build_changelist_url(self, model, query=None):
        return self._build_object_action_url(model, view_name="changelist", query=query)

    def _build_add_url(self, model, args=None):
        return self._build_object_action_url(model, view_name="add", args=args)

    def _build_change_url(self, model, pk):
        return self._build_object_action_url(model, view_name="change", args={"pk": pk})

    def _build_object_action_url(self, model, view_name=None, args=None, query=None):
        """
        https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls

        :param model:
        :param view_name:
        :param query:
        :return:
        """
        allowed_view_names = ("changelist", "add", "history", "delete", "change")

        if view_name is None:
            view_name = "changelist"
        elif view_name not in allowed_view_names:
            raise ValueError(
                'The view_name "{}" is invalid. It must be one of: {}.'.format(
                    view_name, ", ".join(allowed_view_names)
                )
            )

        if args is None:
            args = {}

        url = "{}{}".format(
            reverse(
                "admin:{}_{}_{}".format(
                    model._meta.app_label, model._meta.model_name, view_name
                ),
                args=args,
            ),
            "?{}".format(urlencode(query)) if query else "",
        )
        return url

    def get_object_actions(self, obj):
        return ()

    def _get_object_actions(self, obj):
        return mark_safe(
            " | ".join(
                [
                    '<a href="{url}">{title}</a>'.format(url=action[1], title=action[0])
                    for action in self.get_object_actions(obj)
                ]
            )
        )

    _get_object_actions.allow_tags = True
    _get_object_actions.short_description = _("Acties")


class ListObjectActionsAdminMixin(ObjectActionsAdminMixin):
    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return tuple(list_display) + ("_get_object_actions",)


class EditInlineAdminMixin(object):
    template = "admin/edit_inline/tabular_add_and_edit.html"
    extra = 0
    can_delete = False
    show_change_link = True
    show_add_link = True

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return super().get_fields(request, obj)


# Fix for https://github.com/gradam/django-better-admin-arrayfield/issues/13
class DynamicArrayMixin:
    class Media:
        js = ("js/min/django_better_admin_arrayfield.min.js",)
        css = {"all": ("css/min/django_better_admin_arrayfield.min.css",)}


class AuditTrailAdminMixin(object):
    viewset = None

    def get_viewset(self, request):
        if not self.viewset:
            raise NotImplementedError(
                "'viewset' property should be included to the Admin class"
            )
        viewset = self.viewset

        if isinstance(viewset, str):
            # import module for viewsets with FkOrURLField fields used as filters
            viewset = import_string(viewset)

        return viewset(request=request, format_kwarg=None)

    def add_version_to_request(self, request, viewset, uuid):
        # add versioning to request
        version, scheme = viewset.determine_version(
            request, version=api_settings.DEFAULT_VERSION, uuid=uuid
        )
        request.version, request.versioning_scheme = version, scheme

    def get_serializer_data(self, request, viewset, obj):
        self.add_version_to_request(request, viewset, obj)

        serializer = viewset.get_serializer(obj)
        return serializer.data

    def trail(self, obj, viewset, request, action, data_before, data_after):
        model = obj.__class__
        basename = model._meta.object_name.lower()
        data = data_after or data_before

        if basename == viewset.audit.main_resource:
            main_object = data["url"]
        elif hasattr(viewset, "audittrail_main_resource_key"):
            main_object = data[viewset.audittrail_main_resource_key]
        else:
            main_object = data[viewset.audit.main_resource]

        trail = AuditTrail(
            bron=viewset.audit.component_name,
            applicatie_weergave="admin",
            actie=action,
            actie_weergave=CommonResourceAction.labels.get(action, ""),
            gebruikers_id=request.user.id,
            gebruikers_weergave=request.user.get_full_name(),
            resultaat=0,
            hoofd_object=main_object,
            resource=basename,
            resource_url=data["url"],
            resource_weergave=obj.unique_representation(),
            oud=data_before,
            nieuw=data_after,
        )
        trail.save()

    def save_model(self, request, obj, form, change):
        viewset = self.get_viewset(request)
        if not viewset:
            super().save_model(request, obj, form, change)
            return

        model = obj.__class__
        action = CommonResourceAction.update if change else CommonResourceAction.create

        # data before
        data_before = None
        if change:
            obj_before = model.objects.filter(pk=obj.pk).get()
            data_before = self.get_serializer_data(request, viewset, obj_before)

        super().save_model(request, obj, form, change)

        # data after
        data = self.get_serializer_data(request, viewset, obj)

        if data_before != data:
            self.trail(obj, viewset, request, action, data_before, data)

    def delete_model(self, request, obj):
        viewset = self.get_viewset(request)
        if not viewset:
            super().delete_model(request, obj)
            return

        model = obj.__class__
        basename = model._meta.object_name.lower()
        action = CommonResourceAction.destroy

        data = self.get_serializer_data(request, viewset, obj)

        if basename == viewset.audit.main_resource:
            with transaction.atomic():
                super().delete_model(request, obj)
                AuditTrail.objects.filter(hoofd_object=data["url"]).delete()
                return

        super().delete_model(request, obj)

        self.trail(obj, viewset, request, action, data, None)

    def delete_queryset(self, request, queryset):
        # data before
        for obj in queryset:
            self.delete_model(request, obj)

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        if not hasattr(formset, "viewset"):
            super().save_formset(request, form, formset, change)
            return

        viewset = formset.viewset

        # we need to save data before update/delete
        obj_before_data = {}
        for form in formset.initial_forms:
            obj = form.instance
            if obj.pk is None:
                continue

            obj_before = obj.__class__.objects.get(pk=obj.pk)
            data = self.get_serializer_data(request, viewset, obj_before)
            obj_before_data.update({obj.uuid: data})

        super().save_formset(request, form, formset, change)

        # delete existing
        for obj in formset.deleted_objects:
            data_before = obj_before_data[obj.uuid]

            self.trail(
                obj, viewset, request, CommonResourceAction.destroy, data_before, None
            )

        # change existing
        for obj, changed_data in formset.changed_objects:
            data_before = obj_before_data[obj.uuid]
            data_after = self.get_serializer_data(request, viewset, obj)

            self.trail(
                obj,
                viewset,
                request,
                CommonResourceAction.update,
                data_before,
                data_after,
            )

        # add new
        for obj in formset.new_objects:
            data_after = self.get_serializer_data(request, viewset, obj)
            self.trail(
                obj, viewset, request, CommonResourceAction.create, None, data_after
            )


class AuditTrailInlineAdminMixin(object):
    viewset = None

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        viewset = self.viewset
        if isinstance(viewset, str):
            viewset = import_string(viewset)

        formset.viewset = viewset(request=request, format_kwarg=None)
        return formset


class ExtraContextAdminMixin(object):
    """
    Add this mixin to your admin class to make use of the new function
    `self.get_extra_context` that allows you to add variables to all admin
    views without overriding all of them.

    By default, it adds no extra context.
    """

    def get_extra_context(self, request, object_id=None):
        """
        Override this function to add addition context via the `extra_context`
        parameter. Be arare that `extra_context` can be `None`.

        :param request: The `Request` object.
        :param object_id: The ID of the object in case it's an object view.
        :return: A `dict`.
        """
        return {}

    def _get_extra_context(self, request, extra_context, object_id=None):
        extra_context = extra_context or {}
        extra_context.update(self.get_extra_context(request, object_id))
        return extra_context

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(
            request, extra_context=self._get_extra_context(request, extra_context)
        )

    def add_view(self, request, form_url="", extra_context=None):
        return super().add_view(
            request,
            form_url=form_url,
            extra_context=self._get_extra_context(request, extra_context),
        )

    def history_view(self, request, object_id, extra_context=None):
        return super().history_view(
            request,
            object_id,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )

    def delete_view(self, request, object_id, extra_context=None):
        return super().delete_view(
            request,
            object_id,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )


class UUIDAdminMixin:
    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return tuple(list_display) + ("_get_uuid_display",)

    def _get_uuid_display(self, obj):
        return format_html(
            '<code class="copy-action" data-copy-value="{val}" title="{val}">{shortval}</span>'.format(
                val=str(obj.uuid), shortval=str(obj.uuid)[:6]
            )
        )

    _get_uuid_display.short_description = "UUID"
    _get_uuid_display.allow_tags = True

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        return ("uuid",) + tuple(readonly_fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        # put uuid first in the first fieldset
        fields_general = list(fieldsets[0][1]["fields"])
        if "uuid" in fields_general:
            fields_general.remove("uuid")
        fields_general.insert(0, "uuid")
        fieldsets[0][1]["fields"] = tuple(fields_general)

        return fieldsets


class CMISAdminMixin:
    def has_delete_permission(self, request, obj=None):
        if settings.CMIS_ENABLED:
            return False
        else:
            return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if settings.CMIS_ENABLED:
            return False
        else:
            return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if settings.CMIS_ENABLED:
            return False
        else:
            return super().has_change_permission(request, obj)
