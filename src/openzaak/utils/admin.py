# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urlencode

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.options import InlineModelAdmin
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.base import Model, ModelBase
from django.forms import BaseForm, ModelForm
from django.forms.models import BaseModelFormSet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import ContextMixin

from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import CommonResourceAction


def link_to_related_objects(
    model: ModelBase, obj: Model, rel_field_name: str | None = None
) -> tuple[str, str]:
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

    relation_id_field = relation_field.target_field.name
    query = {f"{relation_field.name}__{relation_id_field}__exact": obj.pk}
    view_name = f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
    changelist_url = f"{reverse(view_name)}?{urlencode(query)}"
    return (
        _("Toon {verbose_name}").format(verbose_name=model._meta.verbose_name_plural),
        changelist_url,
    )


class ObjectActionsAdminMixin(admin.ModelAdmin):
    def _build_changelist_url(
        self, model: ModelBase, query: Mapping[str, object] | None = None
    ) -> str:
        return self._build_object_action_url(model, view_name="changelist", query=query)

    def _build_add_url(
        self, model: ModelBase, args: Mapping[str, object] | None = None
    ) -> str:
        return self._build_object_action_url(model, view_name="add", args=args)

    def _build_change_url(self, model: ModelBase, pk: object) -> str:
        return self._build_object_action_url(model, view_name="change", args={"pk": pk})

    def _build_object_action_url(
        self,
        model: ModelBase,
        view_name: str | None = None,
        args: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
    ) -> str:
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
                args=args,  # pyright: ignore[reportArgumentType]
            ),
            "?{}".format(urlencode(query)) if query else "",
        )
        return url

    def get_object_actions(self, obj: Model) -> Sequence[tuple[str, str]]:
        return ()

    def _get_object_actions(self, obj: Model) -> str:
        return mark_safe(
            " | ".join(
                [
                    '<a href="{url}">{title}</a>'.format(url=action[1], title=action[0])
                    for action in self.get_object_actions(obj)
                ]
            )
        )

    _get_object_actions.allow_tags = True  # pyright: ignore[reportFunctionMemberAccess]
    _get_object_actions.short_description = _("Acties")  # pyright: ignore[reportFunctionMemberAccess]


class ListObjectActionsAdminMixin(ObjectActionsAdminMixin):
    def get_list_display(self, request: HttpRequest):
        list_display = super().get_list_display(request)
        return tuple(list_display) + ("_get_object_actions",)


class EditInlineAdminMixin(InlineModelAdmin):
    template = "admin/edit_inline/tabular_add_and_edit.html"
    extra = 0
    can_delete = False
    show_change_link = True
    show_add_link = True

    def has_add_permission(self, request: HttpRequest, obj: Model | None) -> bool:
        return False

    def get_readonly_fields(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, request: HttpRequest, obj: Model | None = None
    ):
        return super().get_fields(request, obj)


class AuditTrailAdminMixin(admin.ModelAdmin):
    viewset: type[GenericViewSet] | str | None = None

    def get_viewset(self, request: HttpRequest):
        if not self.viewset:
            raise NotImplementedError(
                "'viewset' property should be included to the Admin class"
            )
        viewset = self.viewset

        if isinstance(viewset, str):
            # import module for viewsets with FkOrURLField fields used as filters
            viewset = import_string(viewset)

        return viewset(request=request, format_kwarg=None)

    def add_version_to_request(
        self, request: HttpRequest, viewset, uuid: object
    ) -> None:
        # add versioning to request
        version, scheme = viewset.determine_version(
            request, version=api_settings.DEFAULT_VERSION, uuid=uuid
        )
        request.version, request.versioning_scheme = version, scheme  # pyright: ignore[reportAttributeAccessIssue]

    def get_serializer_data(
        self, request: HttpRequest, viewset, obj: Model
    ) -> Mapping[str, object]:
        self.add_version_to_request(request, viewset, obj)

        serializer = viewset.get_serializer(obj)
        return serializer.data

    def trail(
        self,
        obj: Model,
        viewset,
        request: HttpRequest,
        action: str,
        data_before: Mapping[str, object] | None,
        data_after: Mapping[str, object] | None,
    ) -> None:
        model = obj.__class__
        assert model._meta.object_name
        basename = model._meta.object_name.lower()
        data = data_after or data_before
        assert data is not None

        if basename == viewset.audit.main_resource:
            main_object = data["url"]
        elif hasattr(viewset, "audittrail_main_resource_key"):
            main_object = data[viewset.audittrail_main_resource_key]
        else:
            main_object = data[viewset.audit.main_resource]

        action_labels = dict(
            zip(CommonResourceAction.names, CommonResourceAction.labels)
        )
        trail = AuditTrail(
            bron=viewset.audit.component_name,
            applicatie_weergave="admin",
            actie=action,
            actie_weergave=action_labels.get(action, ""),
            gebruikers_id=request.user.id,  # pyright: ignore[reportAttributeAccessIssue]
            gebruikers_weergave=request.user.get_full_name(),  # pyright: ignore[reportAttributeAccessIssue]
            resultaat=0,
            hoofd_object=main_object,
            resource=basename,
            resource_url=data["url"],
            resource_weergave=obj.unique_representation(),  # pyright: ignore[reportAttributeAccessIssue]
            oud=data_before,
            nieuw=data_after,
        )
        trail.save()

    def save_model(
        self, request: HttpRequest, obj: Model, form: BaseForm, change: bool
    ) -> None:
        viewset = self.get_viewset(request)
        if not viewset:
            super().save_model(request, obj, form, change)
            return

        action = CommonResourceAction.update if change else CommonResourceAction.create

        # data before
        data_before = None
        if change:
            obj_before = obj.__class__.objects.filter(pk=obj.pk).get()
            data_before = self.get_serializer_data(request, viewset, obj_before)

        super().save_model(request, obj, form, change)

        # data after
        data = self.get_serializer_data(request, viewset, obj)

        if data_before != data:
            self.trail(obj, viewset, request, action, data_before, data)

    def delete_model(self, request: HttpRequest, obj: Model) -> None:
        viewset = self.get_viewset(request)
        if not viewset:
            super().delete_model(request, obj)
            return

        model = obj.__class__
        assert model._meta.object_name
        basename = model._meta.object_name.lower()
        action = CommonResourceAction.destroy

        data = self.get_serializer_data(request, viewset, obj)

        if basename == viewset.audit.main_resource:  # pyright: ignore[reportAttributeAccessIssue]
            with transaction.atomic():
                super().delete_model(request, obj)
                AuditTrail.objects.filter(hoofd_object=data["url"]).delete()
                return

        super().delete_model(request, obj)

        self.trail(obj, viewset, request, action, data, None)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Model]) -> None:
        # data before
        for obj in queryset:
            self.delete_model(request, obj)

    def save_formset(
        self,
        request: HttpRequest,
        form: BaseForm,
        formset: BaseModelFormSet[Model, ModelForm[Model]],
        change: bool,
    ) -> None:
        """
        Given an inline formset save it to the database.
        """
        if not hasattr(formset, "viewset"):
            super().save_formset(request, form, formset, change)
            return

        viewset = formset.viewset  # pyright: ignore[reportAttributeAccessIssue]

        # we need to save data before update/delete
        obj_before_data = {}
        for form in formset.initial_forms:
            obj = form.instance
            if obj.pk is None:
                continue

            obj_before = obj.__class__.objects.get(pk=obj.pk)
            data = self.get_serializer_data(request, viewset, obj_before)
            obj_before_data.update({obj.uuid: data})  # pyright: ignore[reportAttributeAccessIssue]

        super().save_formset(request, form, formset, change)

        # delete existing
        for obj in formset.deleted_objects:
            data_before = obj_before_data[obj.uuid]  # pyright: ignore[reportAttributeAccessIssue]

            self.trail(
                obj, viewset, request, CommonResourceAction.destroy, data_before, None
            )

        # change existing
        for obj, changed_data in formset.changed_objects:
            data_before = obj_before_data[obj.uuid]  # pyright: ignore[reportAttributeAccessIssue]
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


class AuditTrailInlineAdminMixin(InlineModelAdmin):
    viewset: type[GenericViewSet] | str | None = None

    def get_formset(
        self, request: HttpRequest, obj: Model | None = None, **kwargs: object
    ):
        formset = super().get_formset(request, obj, **kwargs)

        viewset = self.viewset
        if isinstance(viewset, str):
            viewset = import_string(viewset)
        assert viewset is not None

        formset.viewset = viewset(request=request, format_kwarg=None)  # pyright: ignore[reportAttributeAccessIssue]
        return formset


class ExtraContextAdminMixin(admin.ModelAdmin):
    """
    Add this mixin to your admin class to make use of the new function
    `self.get_extra_context` that allows you to add variables to all admin
    views without overriding all of them.

    By default, it adds no extra context.
    """

    def get_extra_context(
        self, request: HttpRequest, object_id: str | None = None
    ) -> dict[str, object]:
        """
        Override this function to add addition context via the `extra_context`
        parameter. Be arare that `extra_context` can be `None`.

        :param request: The `Request` object.
        :param object_id: The ID of the object in case it's an object view.
        :return: A `dict`.
        """
        return {}

    def _get_extra_context(
        self,
        request: HttpRequest,
        extra_context: dict[str, object] | None,
        object_id: str | None = None,
    ) -> dict[str, object]:
        extra_context = extra_context or {}
        extra_context.update(self.get_extra_context(request, object_id))
        return extra_context

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, object] | None = None
    ) -> HttpResponse:
        return super().changelist_view(
            request, extra_context=self._get_extra_context(request, extra_context)
        )

    def add_view(
        self,
        request: HttpRequest,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        return super().add_view(
            request,
            form_url=form_url,
            extra_context=self._get_extra_context(request, extra_context),
        )

    def history_view(
        self,
        request: HttpRequest,
        object_id: str,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        return super().history_view(
            request,
            object_id,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )

    def delete_view(
        self,
        request: HttpRequest,
        object_id: str,
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        return super().delete_view(
            request,
            object_id,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=self._get_extra_context(request, extra_context, object_id),
        )


class UUIDAdminMixin(admin.ModelAdmin):
    def get_list_display(self, request: HttpRequest):
        list_display = super().get_list_display(request)
        return tuple(list_display) + ("_get_uuid_display",)

    def _get_uuid_display(self, obj: Model) -> str:
        return format_html(
            '<code class="copy-action" data-copy-value="{val}" title="{val}">{shortval}</span>'.format(
                val=str(obj.uuid),  # pyright: ignore[reportAttributeAccessIssue]
                shortval=str(obj.uuid)[:6],  # pyright: ignore[reportAttributeAccessIssue]
            )
        )

    _get_uuid_display.short_description = "UUID"  # pyright: ignore[reportFunctionMemberAccess]
    _get_uuid_display.allow_tags = True  # pyright: ignore[reportFunctionMemberAccess]

    def get_readonly_fields(self, request: HttpRequest, obj: Model | None = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        return ("uuid",) + tuple(readonly_fields)

    def get_fieldsets(self, request: HttpRequest, obj: Model | None = None):
        fieldsets = super().get_fieldsets(request, obj)

        # put uuid first in the first fieldset
        fields_general = list(fieldsets[0][1]["fields"])  # pyright: ignore[reportGeneralTypeIssues]
        if "uuid" in fields_general:
            fields_general.remove("uuid")
        fields_general.insert(0, "uuid")
        fieldsets[0][1]["fields"] = tuple(fields_general)  # pyright: ignore[reportGeneralTypeIssues]

        return fieldsets


class AdminContextMixin(ContextMixin):
    """
    Update custom admin views with all the context info
    """

    admin_site: AdminSite | None = None
    request: HttpRequest

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        assert self.admin_site is not None
        context.update(self.admin_site.each_context(self.request))
        return context


admin.site.unregister(AuditTrail)


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "resource",
        "actie",
        "bron",
        "resultaat",
        "applicatie_weergave",
        "aanmaakdatum",
    )
    list_filter = (
        "bron",
        "resource",
        "actie",
        "applicatie_id",
        "resultaat",
        "aanmaakdatum",
    )
    date_hierarchy = "aanmaakdatum"
    readonly_fields = ("aanmaakdatum",)

    def has_change_permission(self, request: HttpRequest, obj=None):
        return False

    def has_add_permission(self, request: HttpRequest):
        return False
