# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Dict, Tuple

from django.conf import settings
from django.db import models

from django_loose_fk.virtual_models import ProxyMixin

from openzaak.components.besluiten.models import Besluit
from openzaak.utils.query import BlockChangeMixin, LooseFkAuthorizationsFilterMixin


class ZaakAuthorizationsFilterMixin(LooseFkAuthorizationsFilterMixin):
    """
    Filter objects whitelisted by the authorizations.

    For ZRC, authorizations are defined around ``Autorisatie.zaaktype``,
    with a ``max_vertrouwelijkheidaanduiding`` limiting the confidentiality
    level of ``zaken`` (inclusive), and scopes that apply for the
    ``zaaktype`` at hand.

    This means that ``zaken`` are included if, and only if:

    * the ``zaaktype`` is provided in ``authorizations``
    * the scopes for the ``zaaktype`` in each ``authorization`` contain the
      required``scope``
    * the ``zaak.vertrouwelijkheidaanduiding`` is less then or equal to the
      ``authorization.max_vertrouwelijkheidaanduiding``

    :param scope: a (possibly complex) scope that must be granted on the
      authorizations
    :param authorizations: queryset of
      :class:`vng_api_common.authorizations.Autorisatie` objects

    :return: a queryset of filtered results according to the
      authorizations provided
    """

    vertrouwelijkheidaanduiding_use = True
    loose_fk_field = "zaaktype"


class ZaakQuerySet(ZaakAuthorizationsFilterMixin, models.QuerySet):
    pass


class ZaakRelatedQuerySet(ZaakAuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "zaak"


class StatusQuerySet(ZaakRelatedQuerySet):
    def annotate_with_max_datum_status_gezet(self):
        """
        add `max_datum_status_gezet` of all statuses grouped by zaak
        """
        grouped_statussen = (
            self.filter(zaak=models.OuterRef("zaak"))
            .order_by()
            .values("zaak")
            .annotate(max_datum_status_gezet=models.Max("datum_status_gezet"))
            .values("max_datum_status_gezet")
        )
        return self.annotate(max_datum_status_gezet=models.Subquery(grouped_statussen))


class ZaakInformatieObjectQuerySet(BlockChangeMixin, ZaakRelatedQuerySet):
    def filter(self, *args, **kwargs):
        if settings.CMIS_ENABLED and "informatieobject" in kwargs:
            from openzaak.components.documenten.models import (
                EnkelvoudigInformatieObject,
            )

            # If we leave the Document object, the filter will happen on pk, which is None
            # in the CMIS case. This gives an error.
            if isinstance(kwargs["informatieobject"], EnkelvoudigInformatieObject):
                kwargs["informatieobject"] = kwargs["informatieobject"].get_url()

        return super().filter(*args, **kwargs)


class ZaakBesluitQuerySet(BlockChangeMixin, ZaakRelatedQuerySet):
    def create_from(self, besluit: Besluit) -> [models.Model, None]:
        if isinstance(besluit.zaak, ProxyMixin):
            return None

        return self.create(zaak=besluit.zaak, besluit=besluit)

    def delete_for(
        self, besluit: Besluit, previous: bool = False
    ) -> Tuple[int, Dict[str, int]]:
        if isinstance(besluit.zaak, ProxyMixin):
            return (0, {})

        # fetch the instance
        if previous:
            obj = self.get(zaak=besluit.previous_zaak, besluit=besluit)
        else:
            obj = self.get(zaak=besluit.zaak, besluit=besluit)
        return obj.delete()
