from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from ...models import CheckListItem, StatusType
from ..utils.serializers import SourceMappingSerializerMixin


class CheckListItemSerializer(SourceMappingSerializerMixin, ModelSerializer):
    class Meta:
        model = CheckListItem
        ref_name = None  # Inline
        source_mapping = {"naam": "itemnaam"}
        fields = ("naam", "vraagstelling", "verplicht", "toelichting")


class StatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    is_eindstatus = serializers.BooleanField(
        read_only=True,
        help_text=_(
            "Geeft aan dat dit STATUSTYPE een eindstatus betreft. Dit "
            "gegeven is afgeleid uit alle STATUSTYPEn van dit ZAAKTYPE "
            "met het hoogste volgnummer."
        ),
    )

    class Meta:
        model = StatusType
        fields = (
            "url",
            "omschrijving",
            "omschrijving_generiek",
            "statustekst",
            "zaaktype",
            "volgnummer",
            "is_eindstatus",
            "informeren",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "statustype_omschrijving"},
            "omschrijving_generiek": {"source": "statustype_omschrijving_generiek"},
            "volgnummer": {"source": "statustypevolgnummer"},
            "zaaktype": {"lookup_field": "uuid"},
        }
