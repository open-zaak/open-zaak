from rest_framework import permissions


class IsSuperUser(permissions.IsAdminUser):
    def has_permission(self, request, view):
        has_permission = super().has_permission(request, view)
        return has_permission and request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
