# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models

from openzaak.utils.query import BlockChangeMixin, LooseFkAuthorizationsFilterMixin


class BesluitAuthorizationsFilterMixin(LooseFkAuthorizationsFilterMixin):
    """
    Filter objects whitelisted by the authorizations.

    For BRC, authorizations are defined around ``Autorisatie.besluittype``,
    limiting scopes that apply for the ``besluittype`` at hand.

    This means that ``besluiten`` are included if, and only if:

    * the ``besluittype`` is provided in ``authorizations``
    * the scopes for the ``besluittype`` in each ``authorization`` contain the
      required``scope``

    :param scope: a (possibly complex) scope that must be granted on the
      authorizations
    :param authorizations: queryset of
      :class:`vng_api_common.authorizations.Autorisatie` objects

    :return: a queryset of filtered results according to the
      authorizations provided
    """

    vertrouwelijkheidaanduiding_use = False
    loose_fk_field = "besluittype"


class BesluitQuerySet(
    BlockChangeMixin, BesluitAuthorizationsFilterMixin, models.QuerySet
):
    pass


class BesluitRelatedQuerySet(BesluitAuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "besluit"


class BesluitInformatieObjectQuerySet(BlockChangeMixin, BesluitRelatedQuerySet):
    pass
