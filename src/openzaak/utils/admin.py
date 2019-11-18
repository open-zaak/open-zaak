from typing import Tuple
from urllib.parse import urlencode

from django.db.models.base import Model, ModelBase
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from rest_framework.settings import api_settings
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import CommonResourceAction


def link_to_related_objects(model: ModelBase, obj: Model) -> Tuple[str, str]:
    """
    Link to the admin list of ``model`` objects related to ``obj``.

    Introspects the model field relations so that the filter query params can
    be automatically derived and kept in sync when field names change.
    """
    main_model = obj._meta.model
    relation_fields = [
        field
        for field in model._meta.get_fields()
        if getattr(field, "related_model", None) is main_model
    ]
    # TODO: if multiple relations to the same model happen, we need to explicitly
    # pass the field name
    assert len(relation_fields) == 1

    query = {relation_fields[0].name: obj.pk}
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

    def add_version_to_request(self, request, uuid):
        # add versioning to request
        viewset = self.get_viewset(request)
        version, scheme = viewset.determine_version(
            request, version=api_settings.DEFAULT_VERSION, uuid=uuid
        )
        request.version, request.versioning_scheme = version, scheme

    def trail(self, obj, request, action, data_before, data_after):
        model = obj.__class__
        basename = model._meta.object_name.lower()

        viewset = self.get_viewset(request)
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
        model = obj.__class__
        viewset = self.get_viewset(request)
        self.add_version_to_request(request, obj.uuid)

        action = CommonResourceAction.update if change else CommonResourceAction.create

        # data before
        data_before = None
        if change:
            obj_before = model.objects.filter(pk=obj.pk).get()
            serializer_before = viewset.get_serializer(obj_before)
            data_before = serializer_before.data

        super().save_model(request, obj, form, change)

        # data after
        serializer = viewset.get_serializer(obj)
        data = serializer.data

        self.trail(obj, request, action, data_before, data)

    def delete_model(self, request, obj):
        viewset = self.get_viewset(request)
        self.add_version_to_request(request, obj.uuid)

        action = CommonResourceAction.destroy

        # data before
        serializer = viewset.get_serializer(obj)
        data = serializer.data

        super().delete_model(request, obj)

        self.trail(obj, request, action, data, None)

    def delete_queryset(self, request, queryset):
        # data before
        for obj in queryset:
            self.delete_model(request, obj)
