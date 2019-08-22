from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from ...models import Eigenschap, EigenschapSpecificatie
from ...models.choices import FormaatChoices


class EigenschapSpecificatieSerializer(serializers.ModelSerializer):
    class Meta:
        model = EigenschapSpecificatie
        fields = ("groep", "formaat", "lengte", "kardinaliteit", "waardenverzameling")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(FormaatChoices)
        self.fields["formaat"].help_text += f"\n\n{value_display_mapping}"


class EigenschapSerializer(serializers.HyperlinkedModelSerializer):

    specificatie = EigenschapSpecificatieSerializer(
        read_only=True, source="specificatie_van_eigenschap"
    )
    # referentie = EigenschapReferentieSerializer(read_only=True, source='referentie_naar_eigenschap')

    class Meta:
        model = Eigenschap
        fields = ("url", "naam", "definitie", "specificatie", "toelichting", "zaaktype")
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "naam": {"source": "eigenschapnaam"},
            "zaaktype": {"lookup_field": "uuid"},
        }
