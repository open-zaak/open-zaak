from django.utils.translation import ugettext_lazy as _

from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response


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
    def get_concept(self, instance):
        return instance.concept

    def perform_destroy(self, instance):
        if not self.get_concept(instance):
            msg = _("Alleen concepten kunnen worden verwijderd.")
            raise PermissionDenied(detail=msg)

        super().perform_destroy(instance)


class ConceptFilterMixin:
    def get_concept_filter(self):
        return {"concept": False}

    def get_queryset(self):
        qs = super().get_queryset()

        if not hasattr(self, "action") or self.action != "list":
            return qs

        # show only non-concepts by default
        query_params = self.request.query_params or {}
        if "status" in query_params:
            return qs

        return qs.filter(**self.get_concept_filter())


class ConceptMixin(ConceptPublishMixin, ConceptDestroyMixin, ConceptFilterMixin):
    """ mixin for resources which have 'concept' field"""

    pass


class ZaakTypeConceptCreateMixin:
    def perform_create(self, serializer):
        zaaktype = serializer.validated_data["zaaktype"]
        if not zaaktype.concept:
            msg = _("Creating a related object to non-concept object is forbidden")
            raise PermissionDenied(detail=msg)

        super().perform_create(serializer)


class ZaakTypeConceptDestroyMixin(ConceptDestroyMixin):
    def get_concept(self, instance):
        return instance.zaaktype.concept


class ZaakTypeConceptFilterMixin(ConceptFilterMixin):
    def get_concept_filter(self):
        return {"zaaktype__concept": False}


class ZaakTypeConceptMixin(
    ZaakTypeConceptCreateMixin, ZaakTypeConceptDestroyMixin, ZaakTypeConceptFilterMixin
):
    """
    mixin for resources which have FK or one-to-one relations with ZaakType objects,
    which support concept functionality
    """

    pass


class M2MConceptCreateMixin:

    concept_related_fields = []

    def perform_create(self, serializer):
        for field_name in self.concept_related_fields:
            field = serializer.validated_data.get(field_name, [])
            for related_object in field:
                if not related_object.concept:
                    msg = _(
                        f"Relations to a non-concept {field_name} object can't be created"
                    )
                    raise PermissionDenied(detail=msg)

        super().perform_create(serializer)
