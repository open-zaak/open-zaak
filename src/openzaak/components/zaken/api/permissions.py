from openzaak.utils.permissions import AuthRequired


class ZaakAuthRequired(AuthRequired):
    """
    Look at the scopes required for the current action and at zaaktype and vertrouwelijkheidaanduiding
    of current zaak and check that they are present in the AC for this client
    """

    permission_fields = ("zaaktype", "vertrouwelijkheidaanduiding")
    main_resource = "openzaak.components.zaken.api.viewsets.ZaakViewSet"
