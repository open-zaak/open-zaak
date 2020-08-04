# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Union

from django.db import models
from django.utils.translation import ugettext_lazy as _

from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from ..scopes import SCOPE_CATALOGI_FORCED_DELETE


class ConceptPublishMixin:
    @swagger_auto_schema(request_body=no_body)
    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.concept = False
        instance.save()

        serializer = self.get_serializer(instance)

        return Response(serializer.data)


class ConceptDestroyMixin:
    message = _("Alleen concepten kunnen worden verwijderd.")
    code = "non-concept-object"

    def get_concept(self, instance):
        return instance.concept

    def perform_destroy(self, instance):
        forced_delete = self.request.jwt_auth.has_auth(
            scopes=SCOPE_CATALOGI_FORCED_DELETE,
            init_component=self.queryset.model._meta.app_label,
        )

        if not forced_delete:
            if not self.get_concept(instance):
                raise ValidationError({"nonFieldErrors": self.message}, code=self.code)

        super().perform_destroy(instance)


class ConceptFilterMixin:
    def get_concept_filter(self) -> Union[dict, models.Q]:
        return {"concept": False}

    def get_queryset(self):
        qs = super().get_queryset()

        if not hasattr(self, "action") or self.action != "list":
            return qs

        # show only non-concepts by default
        query_params = self.request.query_params or {}
        if "status" in query_params:
            return qs

        filters = self.get_concept_filter()
        if not isinstance(filters, models.Q):
            filters = models.Q(**filters)

        return qs.filter(filters)


class ConceptMixin(ConceptPublishMixin, ConceptDestroyMixin, ConceptFilterMixin):
    """ mixin for resources which have 'concept' field"""

    pass


class ZaakTypeConceptDestroyMixin(ConceptDestroyMixin):
    message = _(
        "Objecten gerelateerd aan non-concept zaaktypen kunnen niet verwijderd worden."
    )
    code = "non-concept-zaaktype"

    def get_concept(self, instance):
        return instance.zaaktype.concept


class ZaakTypeConceptFilterMixin(ConceptFilterMixin):
    def get_concept_filter(self):
        return {"zaaktype__concept": False}


class ZaakTypeConceptMixin(ZaakTypeConceptDestroyMixin, ZaakTypeConceptFilterMixin):
    """
    mixin for resources which have FK or one-to-one relations with ZaakType objects,
    which support concept functionality
    """

    pass


class M2MConceptDestroyMixin:
    def perform_destroy(self, instance):
        forced_delete = self.request.jwt_auth.has_auth(
            scopes=SCOPE_CATALOGI_FORCED_DELETE,
            init_component=self.queryset.model._meta.app_label,
        )

        if not forced_delete:
            for field_name in self.concept_related_fields:
                field = getattr(instance, field_name)
                related_non_concepts = field.filter(concept=False)
                if related_non_concepts.exists():
                    msg = _(
                        f"Objects related to non-concept {field_name} can't be destroyed"
                    )
                    raise ValidationError(
                        {"nonFieldErrors": msg}, code="non-concept-relation"
                    )

        super().perform_destroy(instance)
