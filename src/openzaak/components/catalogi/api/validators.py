# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ErrorDetail
from rest_framework.serializers import Serializer, ValidationError
from rest_framework.settings import api_settings
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)

from openzaak.client import fetch_object
from openzaak.components.catalogi.api.scopes import SCOPE_CATALOGI_FORCED_WRITE
from openzaak.utils.serializers import get_from_serializer_data_or_instance

from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..utils import has_overlapping_objects
from ..validators import (
    validate_brondatumarchiefprocedure,
    validate_zaaktype_for_publish,
)


class GeldigheidValidator:
    """
    Validate that the (new) object is unique between a start and end date.

    Empty end date is an open interval, which means that the object cannot
    be created after the start date.
    """

    code = "overlap"
    message = _(
        "Dit {} komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
    )
    requires_context = True

    def __init__(self, omschrijving_field="omschrijving"):
        self.omschrijving_field = omschrijving_field

    def get_field_data(self, attrs, serializer):

        catalogus = get_from_serializer_data_or_instance("catalogus", attrs, serializer)
        begin_geldigheid = get_from_serializer_data_or_instance(
            "begin_geldigheid", attrs, serializer
        )
        einde_geldigheid = get_from_serializer_data_or_instance(
            "einde_geldigheid", attrs, serializer
        )
        omschrijving = get_from_serializer_data_or_instance(
            self.omschrijving_field, attrs, serializer
        )

        concept = get_from_serializer_data_or_instance("concept", attrs, serializer)
        if concept is None:
            concept = True

        return catalogus, begin_geldigheid, einde_geldigheid, omschrijving, concept

    def __call__(self, attrs, serializer):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer, "instance", None)
        base_model = getattr(serializer.Meta, "model", None)

        (
            catalogus,
            begin_geldigheid,
            einde_geldigheid,
            omschrijving,
            concept,
        ) = self.get_field_data(attrs, serializer)

        if has_overlapping_objects(
            model_manager=base_model._default_manager,
            catalogus=catalogus,
            omschrijving_query={self.omschrijving_field: omschrijving},
            begin_geldigheid=begin_geldigheid,
            einde_geldigheid=einde_geldigheid,
            instance=instance,
            concept=concept,
        ):
            # are we patching eindeGeldigheid?
            changing_published_geldigheid = serializer.partial and list(attrs) == [
                "datum_einde_geldigheid"
            ]
            error_field = (
                "einde_geldigheid"
                if changing_published_geldigheid
                else "begin_geldigheid"
            )
            raise ValidationError(
                {error_field: self.message.format(base_model._meta.verbose_name)},
                code=self.code,
            )


class GeldigheidPublishValidator(GeldigheidValidator):
    def get_field_data(self, attrs, serializer):
        begin_geldigheid = serializer.instance.datum_begin_geldigheid
        einde_geldigheid = serializer.instance.datum_einde_geldigheid
        catalogus = serializer.instance.catalogus
        omschrijving = getattr(serializer.instance, self.omschrijving_field)

        concept = attrs["concept"]
        return catalogus, begin_geldigheid, einde_geldigheid, omschrijving, concept


def get_by_source(obj, path: str):
    """
    support nested path with "."
    """
    bits = path.split(".", maxsplit=1)
    value = obj.get(bits[0]) if isinstance(obj, dict) else getattr(obj, bits[0], None)
    if len(bits) == 1:
        return value
    return get_by_source(value, bits[1])


class RelationCatalogValidator:
    code = "relations-incorrect-catalogus"
    message = _("The {} has catalogus different from created object")
    requires_context = True

    def __init__(
        self,
        relation_field: str,
        catalogus_field="catalogus",
        relation_field_catalogus_path="catalogus",
    ):
        self.relation_field = relation_field
        self.catalogus_field = catalogus_field
        self.relation_field_catalogus_path = relation_field_catalogus_path

    def __call__(self, attrs: dict, serializer):
        instance = getattr(serializer, "instance", None)
        relations = attrs.get(self.relation_field)
        catalogus = get_by_source(attrs, self.catalogus_field) or get_by_source(
            instance, self.catalogus_field
        )

        if not relations:
            return

        if not isinstance(relations, list):
            relations = [relations]

        for relation in relations:
            relation_catalogus = get_by_source(
                relation, self.relation_field_catalogus_path
            )
            if relation_catalogus != catalogus:
                raise ValidationError(
                    self.message.format(self.relation_field), code=self.code
                )


class ProcesTypeValidator:
    code = "procestype-mismatch"
    message = _("{} should belong to the same procestype as {}")

    def __init__(self, relation_field: str, zaaktype_field="zaaktype"):
        self.relation_field = relation_field
        self.zaaktype_field = zaaktype_field

    def __call__(self, attrs: dict):
        selectielijstklasse_url = attrs.get(self.relation_field)
        zaaktype = attrs.get(self.zaaktype_field)

        if not selectielijstklasse_url:
            return

        selectielijstklasse = fetch_object(selectielijstklasse_url)

        if selectielijstklasse["procesType"] != zaaktype.selectielijst_procestype:
            raise ValidationError(
                self.message.format(self.relation_field, self.zaaktype_field),
                code=self.code,
            )


class ProcestermijnAfleidingswijzeValidator:
    code = "invalid-afleidingswijze-for-procestermijn"
    message = _(
        "afleidingswijze cannot be {} when selectielijstklasse.procestermijn is {}"
    )

    def __init__(
        self,
        selectielijstklasse_field: str,
        archiefprocedure_field="brondatum_archiefprocedure",
    ):
        self.selectielijstklasse_field = selectielijstklasse_field
        self.archiefprocedure_field = archiefprocedure_field

    def __call__(self, attrs: dict):
        selectielijstklasse_url = attrs.get(self.selectielijstklasse_field)
        archiefprocedure = attrs.get(self.archiefprocedure_field)

        if not selectielijstklasse_url or not archiefprocedure:
            return

        selectielijstklasse = fetch_object(selectielijstklasse_url)
        procestermijn = selectielijstklasse["procestermijn"]
        afleidingswijze = archiefprocedure["afleidingswijze"]

        error = False

        if not procestermijn:
            return

        if (
            procestermijn == Procestermijn.nihil
            and afleidingswijze != Afleidingswijze.afgehandeld
        ) or (
            procestermijn != Procestermijn.nihil
            and afleidingswijze == Afleidingswijze.afgehandeld
        ):
            error = True
        elif (
            procestermijn == Procestermijn.ingeschatte_bestaansduur_procesobject
            and afleidingswijze != Afleidingswijze.termijn
        ) or (
            procestermijn != Procestermijn.ingeschatte_bestaansduur_procesobject
            and afleidingswijze == Afleidingswijze.termijn
        ):
            error = True

        if error:
            raise ValidationError(
                self.message.format(afleidingswijze, procestermijn), code=self.code
            )


class BrondatumArchiefprocedureValidator:
    empty_code = "must-be-empty"
    empty_message = _("This field must be empty for afleidingswijze `{}`")
    required_code = "required"
    required_message = _("This field is required for afleidingswijze `{}`")
    requires_context = True

    def __init__(self, archiefprocedure_field="brondatum_archiefprocedure"):
        self.archiefprocedure_field = archiefprocedure_field

    def __call__(self, attrs: dict, serializer: Serializer):
        instance = getattr(serializer, "instance", None)
        partial = getattr(serializer, "partial", None)
        archiefprocedure = attrs.get(self.archiefprocedure_field)
        if archiefprocedure is None:
            archiefnominatie = attrs.get(
                "archiefnominatie", getattr(instance, "archiefnominatie", None)
            )
            if not partial and archiefnominatie != Archiefnominatie.blijvend_bewaren:
                raise ValidationError(
                    {
                        self.archiefprocedure_field: _(
                            "This field is required if archiefnominatie is {an}"
                        ).format(an=archiefnominatie)
                    },
                    code="required",
                )
            return

        afleidingswijze = archiefprocedure["afleidingswijze"]
        error, empty, required = validate_brondatumarchiefprocedure(archiefprocedure)

        if error:
            error_dict = {}
            for fieldname in empty:
                error_dict.update(
                    {
                        f"{self.archiefprocedure_field}.{fieldname}": ErrorDetail(
                            self.empty_message.format(afleidingswijze), self.empty_code
                        )
                    }
                )
            for fieldname in required:
                error_dict.update(
                    {
                        f"{self.archiefprocedure_field}.{fieldname}": ErrorDetail(
                            self.required_message.format(afleidingswijze),
                            self.required_code,
                        )
                    }
                )
            raise ValidationError(error_dict)


class ZaakTypeInformatieObjectTypeCatalogusValidator:
    code = "relations-incorrect-catalogus"
    message = _("The zaaktype has catalogus different from informatieobjecttype")
    requires_context = True

    def __call__(self, attrs: dict, serializer):
        instance = getattr(serializer, "instance", None)
        zaaktype = attrs.get("zaaktype") or instance.zaaktype
        informatieobjecttype = (
            attrs.get("informatieobjecttype") or instance.informatieobjecttype
        )

        if zaaktype.catalogus != informatieobjecttype.catalogus:
            raise ValidationError(self.message, code=self.code)


class DeelzaaktypeCatalogusValidator:
    code = "relations-incorrect-catalogus"
    message = _("Hoofd- en deelzaaktypen moeten tot dezelfde catalogus behoren")
    requires_context = True

    def __call__(self, attrs: dict, serializer):
        instance = getattr(serializer, "instance", None)
        default_deelzaaktypen = instance.deelzaaktypen.all() if instance else []
        default_catalogus = instance.catalogus if instance else None

        deelzaaktypen = attrs.get("deelzaaktypen") or default_deelzaaktypen
        catalogus = attrs.get("catalogus") or default_catalogus

        # can't run validator...
        if catalogus is None:
            return

        if any(
            deelzaaktype.catalogus_id != catalogus.id for deelzaaktype in deelzaaktypen
        ):
            raise ValidationError({"deelzaaktypen": self.message}, code=self.code)


def is_force_write(serializer) -> bool:
    request = serializer.context["request"]

    # if no jwt_auth -> it's used in the admin of the management command
    if not hasattr(request, "jwt_auth"):
        return True

    return request.jwt_auth.has_auth(
        scopes=SCOPE_CATALOGI_FORCED_WRITE,
        init_component=serializer.Meta.model._meta.app_label,
    )


class ConceptUpdateValidator:
    message = _("Het is niet toegestaan om een non-concept object bij te werken")
    code = "non-concept-object"
    requires_context = True

    def __call__(self, attrs, serializer):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer, "instance", None)

        if not instance:
            return

        # New in Catalogi 1.2: allow concept update for a specific scope
        if is_force_write(serializer):
            return

        # updating eindeGeldigheid is allowed through patch requests
        if serializer.partial and list(attrs.keys()) == ["datum_einde_geldigheid"]:
            return

        if not instance.concept:
            raise ValidationError(self.message, code=self.code)


class VerlengingsValidator:
    message = _("Verlengingstermijn must be set if verlengingMogelijk is true")
    code = "verlenging-mismatch"

    def __call__(self, attrs):
        if attrs.get("verlenging_mogelijk") and not attrs.get("verlengingstermijn"):
            raise ValidationError(self.message, code=self.code)


class ZaakTypeConceptValidator:
    """
    Validator that checks for related non-concept zaaktype when doing
    updates/creates
    """

    message = _(
        "Updating an object that has a relation to a non-concept zaaktype is forbidden"
    )
    code = "non-concept-zaaktype"
    requires_context = True

    def __call__(self, attrs, serializer):
        # New in Catalogi 1.2: allow concept update for a specific scope
        if is_force_write(serializer):
            return

        instance = getattr(serializer, "instance", None)

        if instance:
            zaaktype = instance.zaaktype
            if not zaaktype.concept:
                raise ValidationError(self.message, code=self.code)

        zaaktype_in_attrs = attrs.get("zaaktype")
        if zaaktype_in_attrs:
            if not zaaktype_in_attrs.concept:
                msg = _("Creating a relation to non-concept zaaktype is forbidden")
                raise ValidationError(msg, code=self.code)


class M2MConceptCreateValidator:
    """
    Validator that checks for related non-concepts in M2M fields when creating
    objects
    """

    code = "non-concept-relation"
    requires_context = True

    def __init__(self, concept_related_fields):
        self.concept_related_fields = concept_related_fields

    def __call__(self, attrs, serializer):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer, "instance", None)
        if instance:
            return

        # New in Catalogi 1.2: allow concept create for a specific scope
        if is_force_write(serializer):
            return

        for field_name in self.concept_related_fields:
            field = attrs.get(field_name, [])
            for related_object in field:
                if not related_object.concept:
                    msg = _(
                        f"Relations to non-concept {field_name} object can't be created"
                    )
                    raise ValidationError(msg, code=self.code)


class M2MConceptUpdateValidator:
    """
    Validator that checks for related non-concepts in M2M fields when doing
    updates
    """

    code = "non-concept-relation"
    requires_context = True

    def __init__(self, concept_related_fields):
        self.concept_related_fields = concept_related_fields

    def __call__(self, attrs, serializer):
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer, "instance", None)
        request = serializer.context["request"]
        if not instance:
            return

        # New in Catalogi 1.2: allow concept update for a specific scope
        if is_force_write(serializer):
            return

        einde_geldigheid = attrs.get("datum_einde_geldigheid")
        if einde_geldigheid and len(request.data) == 1:
            return

        for field_name in self.concept_related_fields:
            field = getattr(instance, field_name)
            related_non_concepts = field.filter(concept=False)
            if related_non_concepts.exists():
                msg = _(f"Objects related to non-concept {field_name} can't be updated")
                raise ValidationError(msg, code=self.code)

            # Validate that no new relations are created to resources with
            # non-concept status
            field_in_attrs = attrs.get(field_name)
            if field_in_attrs:
                for relation in field_in_attrs:
                    if not relation.concept:
                        msg = _(
                            f"Objects can't be updated with a relation to non-concept {field_name}"
                        )
                        raise ValidationError(msg, code=self.code)


class RelationZaaktypeValidator:
    code = "relations-incorrect-zaaktype"
    message = _("The {} has zaaktype different from created object")
    requires_context = True

    def __init__(
        self,
        relation_field: str,
    ):
        self.relation_field = relation_field

    def __call__(self, attrs: dict, serializer):
        instance = getattr(serializer, "instance", None)
        relations = attrs.get(self.relation_field)
        zaaktype = attrs.get("zaaktype") or instance.zaaktype

        if not relations:
            return

        if not isinstance(relations, list):
            relations = [relations]

        for relation in relations:
            if relation.zaaktype != zaaktype:
                raise ValidationError(
                    self.message.format(self.relation_field), code=self.code
                )


class BronZaakTypeValidator:
    code = "invalid-bronzaaktype-for-broncatalogus"
    message = _("Both broncatalogus and bronzaaktype should be provided")

    def __call__(self, attrs: dict):
        broncatalogus = attrs.get("broncatalogus")
        bronzaaktype = attrs.get("bronzaaktype")

        if bool(broncatalogus) != bool(bronzaaktype):
            raise ValidationError(self.message, code=self.code)


class StartBeforeEndValidator:
    """
    Validate that start date is before the end date
    """

    code = "date-mismatch"
    message = _("{} should be before {}.")
    requires_context = True

    def __init__(
        self, start_date_field="begin_geldigheid", end_date_field="einde_geldigheid"
    ):
        self.start_date_field = start_date_field
        self.end_date_field = end_date_field

    def __call__(self, attrs, serializer):
        start_date = get_from_serializer_data_or_instance(
            self.start_date_field, attrs, serializer
        )
        end_date = get_from_serializer_data_or_instance(
            self.end_date_field, attrs, serializer
        )

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                self.message.format(self.start_date_field, self.end_date_field),
                code=self.code,
            )


class ZaakTypeRelationsPublishValidator:
    """
    Validate that the ZaakType object has the correct relations for publishing
    """

    code = "concept-relation"
    requires_context = True

    def __call__(self, attrs, serializer):
        instance = getattr(serializer, "instance", None)

        validation_errors = validate_zaaktype_for_publish(instance)
        serializer_errors = dict()

        for field, error in validation_errors:
            if field is None:
                field = api_settings.NON_FIELD_ERRORS_KEY

            field_errors = serializer_errors.get(field, [])
            field_errors.append(error)
            serializer_errors[field] = field_errors

        if len(serializer_errors) > 0:
            raise ValidationError(serializer_errors, code=self.code)
