from django.db import models
from django.db.models import Case, IntegerField, Value, When

from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.scopes import Scope


class AuthorizationsFilterMixin:
    authorizations_lookup = None

    def filter_for_authorizations(
        self, scope: Scope, authorizations: models.QuerySet
    ) -> models.QuerySet:
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
        # keep a list of allowed zaaktypen
        zaaktypen = []

        prefix = (
            "" if not self.authorizations_lookup else f"{self.authorizations_lookup}__"
        )

        # annotate the queryset so we can map a string value to a logical number
        order_case = VertrouwelijkheidsAanduiding.get_order_expression(
            f"{prefix}vertrouwelijkheidaanduiding"
        )

        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``zaaktype``
        vertrouwelijkheidaanduiding_whens = []
        for authorization in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(authorization.scopes):
                continue

            # this zaaktype is allowed
            zaaktypen.append(authorization.zaaktype)

            # extract the order and map it to the database value
            choice_item = VertrouwelijkheidsAanduiding.get_choice(
                authorization.max_vertrouwelijkheidaanduiding
            )
            vertrouwelijkheidaanduiding_whens.append(
                When(
                    **{f"{prefix}zaaktype": authorization.zaaktype},
                    then=Value(choice_item.order),
                )
            )

        # apply the order annnotation so we can filter later
        annotations = {f"{prefix}_va_order": order_case}
        # filtering:
        # * only allow the white-listed zaaktypen, explicitly
        # * apply the filtering to limit cases within case-types to the maximal
        #   confidentiality level
        filters = {
            f"{prefix}zaaktype__in": zaaktypen,
            f"{prefix}_va_order__lte": Case(
                *vertrouwelijkheidaanduiding_whens, output_field=IntegerField()
            ),
        }

        # bring it all together now to build the resulting queryset
        queryset = self.annotate(**annotations).filter(**filters)
        return queryset


class ZaakQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    pass


class ZaakRelatedQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "zaak"
