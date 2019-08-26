from openzaak.utils.permissions import AuthRequired


class ZaakAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at zaaktype and vertrouwelijkheidaanduiding
    of current zaak and check that they are present in the AC for this client
    """

    permission_fields = ("zaaktype", "vertrouwelijkheidaanduiding")
    main_resource = "openzaak.components.zaken.api.viewsets.ZaakViewSet"


class ZaakNestedAuthRequired(ZaakAuthRequired):
    def has_permission_related(self, request, view, scopes, component) -> bool:
        main_object = view._get_zaak()
        main_object_data = self.format_data(main_object, request)

        fields = self.get_fields(main_object_data)
        return request.jwt_auth.has_auth(scopes, component, **fields)
