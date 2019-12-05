from openzaak.utils.permissions import AuthRequired


class AutorisatiesAuthRequired(AuthRequired):
    def get_component(self, view) -> str:
        assert view.__module__ == "openzaak.components.autorisaties.api.viewsets"
        return "autorisaties"
