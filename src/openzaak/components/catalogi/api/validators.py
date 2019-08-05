from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from openzaak.components.catalogi.models import ZaakType
from rest_framework.serializers import ValidationError


class ZaaktypeGeldigheidValidator:
    """
    Validate that the (new) object is unique between a start and end date.

    Empty end date is an open interval, which means that the object cannot
    be created after the start date.
    """
    message = _("Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode.")
    code = "overlap"

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, 'instance', None)

    def __call__(self, attrs):
        catalogus = attrs["catalogus"]
        zaaktype_omschrijving = attrs["zaaktype_omschrijving"]
        datum_begin_geldigheid = attrs["datum_begin_geldigheid"]
        datum_einde_geldigheid = attrs.get("datum_einde_geldigheid")

        query = ZaakType.objects.filter(
            Q(catalogus=catalogus),
            Q(zaaktype_omschrijving=zaaktype_omschrijving),
            Q(datum_einde_geldigheid=None)
            | Q(datum_einde_geldigheid__gte=datum_begin_geldigheid)  # noqa
        )
        if datum_einde_geldigheid is not None:
            query = query.filter(datum_begin_geldigheid__lte=datum_einde_geldigheid)

        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        # regel voor zaaktype omschrijving
        if query.exists():
            raise ValidationError({"begin_geldigheid": self.message}, code=self.code)
