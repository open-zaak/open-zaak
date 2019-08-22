from django.apps import apps
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

        For DRC, authorizations are defined around ``Autorisatie.informatieobjecttype``,
        with a ``max_vertrouwelijkheidaanduiding`` limiting the confidentiality
        level of ``informatieobjecten`` (inclusive), and scopes that apply for the
        ``informatieobjecttype`` at hand.

        This means that ``informatieobjecten`` are included if, and only if:

        * the ``informatieobjecttype`` is provided in ``authorizations``
        * the scopes for the ``informatieobjecttype`` in each ``authorization`` contain the
          required``scope``
        * the ``informatieobjecttype.vertrouwelijkheidaanduiding`` is less then or equal to the
          ``authorization.max_vertrouwelijkheidaanduiding``

        :param scope: a (possibly complex) scope that must be granted on the
          authorizations
        :param authorizations: queryset of
          :class:`vng_api_common.authorizations.Autorisatie` objects

        :return: a queryset of filtered results according to the
          authorizations provided
        """
        # keep a list of allowed informatieobjecttypen
        informatieobjecttypen = []

        # annotate the queryset so we can map a string value to a logical number
        order_case = VertrouwelijkheidsAanduiding.get_order_expression(
            "vertrouwelijkheidaanduiding"
        )

        # build the case/when to map the max_vertrouwelijkheidaanduiding based
        # on the ``informatieobjecttype``
        vertrouwelijkheidaanduiding_whens = []
        for authorization in authorizations:
            # test if this authorization has the scope that's needed
            if not scope.is_contained_in(authorization.scopes):
                continue

            # this informatieobjecttype is allowed
            informatieobjecttypen.append(authorization.informatieobjecttype)

            # extract the order and map it to the database value
            choice_item = VertrouwelijkheidsAanduiding.get_choice(
                authorization.max_vertrouwelijkheidaanduiding
            )
            vertrouwelijkheidaanduiding_whens.append(
                When(
                    **{"informatieobjecttype": authorization.informatieobjecttype},
                    then=Value(choice_item.order),
                )
            )

        # apply the order annnotation so we can filter later
        annotations = {"_va_order": order_case}
        # filtering:
        # * only allow the white-listed informatieobjecttypen, explicitly
        # * apply the filtering to limit cases within case-types to the maximal
        #   confidentiality level
        filters = {
            "informatieobjecttype__in": informatieobjecttypen,
            "_va_order__lte": Case(
                *vertrouwelijkheidaanduiding_whens, output_field=IntegerField()
            ),
        }
        if self.authorizations_lookup:
            # If the current queryset is not an InformatieObjectQuerySet, first
            # retrieve the canonical IDs of EnkelvoudigInformatieObjects
            # for which the user is authorized and then return the objects
            # related to those EnkelvoudigInformatieObjectCanonicals
            model = apps.get_model("documenten", "EnkelvoudigInformatieObject")
            filtered = (
                model.objects.annotate(**annotations)
                .filter(**filters)
                .values("canonical")
            )
            queryset = self.filter(informatieobject__in=filtered)
        # bring it all together now to build the resulting queryset
        else:
            queryset = self.annotate(**annotations).filter(**filters)
        return queryset


class InformatieobjectQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    pass


class InformatieobjectRelatedQuerySet(AuthorizationsFilterMixin, models.QuerySet):
    authorizations_lookup = "informatieobject"
