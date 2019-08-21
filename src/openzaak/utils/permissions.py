from rest_framework.request import Request


class AuthComponentMixin:
    def get_component(self, view) -> str:
        return view.queryset.model._meta.app_label

    def has_permission(self, request: Request, view) -> bool:
        component = self.get_component(view)
        request.jwt_auth.set_component(component)

        print('component=', component)
        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        component = self.get_component(view)
        request.jwt_auth.set_component(component)

        print('component=', component)
        return super().has_object_permission(request, view, obj)
