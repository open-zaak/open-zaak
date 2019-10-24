from rest_framework import serializers
from vng_api_common.serializers import add_choice_values_help_text

from ...constants import RichtingChoices
from ...models import ZaakInformatieobjectType
from ..validators import ZaakInformatieObjectTypeCatalogusValidator


class ZaakTypeInformatieObjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Represent a ZaakTypeInformatieObjectType.

    Relatie met informatieobjecttype dat relevant is voor zaaktype.
    """

    class Meta:
        model = ZaakInformatieobjectType
        fields = (
            "url",
            "zaaktype",
            "informatieobjecttype",
            "volgnummer",
            "richting",
            "statustype",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "zaaktype": {"lookup_field": "uuid"},
            "informatieobjecttype": {"lookup_field": "uuid"},
            "statustype": {"lookup_field": "uuid"},
        }
        validators = [ZaakInformatieObjectTypeCatalogusValidator()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(RichtingChoices)
        self.fields["richting"].help_text += f"\n\n{value_display_mapping}"
