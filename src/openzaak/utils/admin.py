from urllib.parse import urlencode

from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


class ObjectActionsAdminMixin(object):
    def _build_changelist_url(self, model, query=None):
        return self._build_object_action_url(model, view_name='changelist', query=query)

    def _build_add_url(self, model, args=None):
        return self._build_object_action_url(model, view_name='add', args=args)

    def _build_change_url(self, model, pk):
        return self._build_object_action_url(model, view_name='change', args={'pk': pk})

    def _build_object_action_url(self, model, view_name=None, args=None, query=None):
        """
        https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls

        :param model:
        :param view_name:
        :param query:
        :return:
        """
        allowed_view_names = ('changelist', 'add', 'history', 'delete', 'change')

        if view_name is None:
            view_name = 'changelist'
        elif view_name not in allowed_view_names:
            raise ValueError('The view_name "{}" is invalid. It must be one of: {}.'.format(
                view_name, ', '.join(allowed_view_names)))

        if args is None:
            args = {}

        url = '{}{}'.format(
            reverse('admin:{}_{}_{}'.format(model._meta.app_label, model._meta.model_name, view_name), args=args),
            '?{}'.format(urlencode(query)) if query else '')
        return url

    def get_object_actions(self, obj):
        return ()

    def _get_object_actions(self, obj):
        return mark_safe(' | '.join([
            '<a href="{url}">{title}</a>'.format(url=action[1], title=action[0])
            for action in self.get_object_actions(obj)
        ]))
    _get_object_actions.allow_tags = True
    _get_object_actions.short_description = _('Acties')


class ListObjectActionsAdminMixin(ObjectActionsAdminMixin):
    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return tuple(list_display) + ('_get_object_actions', )


class EditInlineAdminMixin(object):
    template = 'admin/edit_inline/tabular_add_and_edit.html'
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return super().get_fields(request, obj)
