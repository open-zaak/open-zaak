from openzaak.utils.permissions import AuthRequired


class InformationObjectAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at informatieobjecttype and vertrouwelijkheidaanduiding
    of current informatieobject and check that they are present in the AC for this client
    """

    permission_fields = ("informatieobjecttype", "vertrouwelijkheidaanduiding")
    main_resource = (
        "openzaak.components.documenten.api.viewsets.EnkelvoudigInformatieObjectViewSet"
    )

    def has_object_permission_related(
        self, request, view, obj, scopes, component
    ) -> bool:
        main_object = getattr(obj, view.permission_main_object).latest_version
        main_object_data = self.format_data(main_object, request)

        fields = self.get_fields(main_object_data)
        return request.jwt_auth.has_auth(scopes, component, **fields)
