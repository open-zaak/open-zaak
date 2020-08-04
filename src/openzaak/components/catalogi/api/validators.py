# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ErrorDetail
from rest_framework.serializers import ValidationError
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)

from openzaak.client import fetch_object

from ..constants import SelectielijstKlasseProcestermijn as Procestermijn
from ..utils import get_overlapping_zaaktypes


class ZaaktypeGeldigheidValidator:
    """
    Validate that the (new) object is unique between a start and end date.

    Empty end date is an open interval, which means that the object cannot
    be created after the start date.
    """

    message = _(
        "Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode."
    )
    code = "overlap"

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs):
        catalogus = attrs.get("catalogus") or self.instance.catalogus
        zaaktype_omschrijving = (
            attrs.get("zaaktype_omschrijving") or self.instance.zaaktype_omschrijving
        )
        datum_begin_geldigheid = (
            attrs.get("datum_begin_geldigheid") or self.instance.datum_begin_geldigheid
        )
        current_einde_geldigheid = (
            self.instance.datum_einde_geldigheid if self.instance is not None else None
        )
        datum_einde_geldigheid = (
            attrs.get("datum_einde_geldigheid") or current_einde_geldigheid
        )

        query = get_overlapping_zaaktypes(
            catalogus,
            zaaktype_omschrijving,
            datum_begin_geldigheid,
            datum_einde_geldigheid,
            self.instance,
        )

        # regel voor zaaktype omschrijving
        if query.exists():
            raise ValidationError({"begin_geldigheid": self.message}, code=self.code)


class RelationCatalogValidator:
    code = "relations-incorrect-catalogus"
    message = _("The {} has catalogus different from created object")

    def __init__(self, relation_field: str, catalogus_field="catalogus"):
        self.relation_field = relation_field
        self.catalogus_field = catalogus_field

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs: dict):
        relations = attrs.get(self.relation_field)
        catalogus = attrs.get(self.catalogus_field) or self.instance.catalogus

        if not relations:
            return

        if not isinstance(relations, list):
            relations = [relations]

        for relation in relations:
            if relation.catalogus != catalogus:
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

        selectielijstklasse = fetch_object("resultaat", selectielijstklasse_url)

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

        selectielijstklasse = fetch_object("resultaat", selectielijstklasse_url)
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


def validate_brondatumarchiefprocedure(data: dict, mapping: dict):
    error = False
    empty = []
    required = []
    for key, value in mapping.items():
        if bool(data[key]) != value:
            error = True
            if value:
                required.append(key)
            else:
                empty.append(key)
    return error, empty, required


class BrondatumArchiefprocedureValidator:
    empty_code = "must-be-empty"
    empty_message = _("This field must be empty for afleidingswijze `{}`")
    required_code = "required"
    required_message = _("This field is required for afleidingswijze `{}`")

    def __init__(self, archiefprocedure_field="brondatum_archiefprocedure"):
        self.archiefprocedure_field = archiefprocedure_field

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)
        self.partial = getattr(serializer, "partial", None)

    def __call__(self, attrs: dict):
        archiefprocedure = attrs.get(self.archiefprocedure_field)
        if archiefprocedure is None:
            archiefnominatie = attrs.get(
                "archiefnominatie", getattr(self.instance, "archiefnominatie", None)
            )
            if (
                not self.partial
                and archiefnominatie != Archiefnominatie.blijvend_bewaren
            ):
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

        mapping = {
            Afleidingswijze.afgehandeld: {
                "procestermijn": False,
                "datumkenmerk": False,
                "einddatum_bekend": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.ander_datumkenmerk: {
                "procestermijn": False,
                "datumkenmerk": True,
                "objecttype": True,
                "registratie": True,
            },
            Afleidingswijze.eigenschap: {
                "procestermijn": False,
                "datumkenmerk": True,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.gerelateerde_zaak: {
                "procestermijn": False,
                "datumkenmerk": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.hoofdzaak: {
                "procestermijn": False,
                "datumkenmerk": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.ingangsdatum_besluit: {
                "procestermijn": False,
                "datumkenmerk": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.termijn: {
                "procestermijn": True,
                "datumkenmerk": False,
                "einddatum_bekend": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.vervaldatum_besluit: {
                "procestermijn": False,
                "datumkenmerk": False,
                "objecttype": False,
                "registratie": False,
            },
            Afleidingswijze.zaakobject: {
                "procestermijn": False,
                "datumkenmerk": True,
                "objecttype": True,
                "registratie": False,
            },
        }

        error, empty, required = validate_brondatumarchiefprocedure(
            archiefprocedure, mapping[afleidingswijze]
        )

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

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs: dict):
        zaaktype = attrs.get("zaaktype") or self.instance.zaaktype
        informatieobjecttype = (
            attrs.get("informatieobjecttype") or self.instance.informatieobjecttype
        )

        if zaaktype.catalogus != informatieobjecttype.catalogus:
            raise ValidationError(self.message, code=self.code)


class DeelzaaktypeCatalogusValidator:
    code = "relations-incorrect-catalogus"
    message = _("Hoofd- en deelzaaktypen moeten tot dezelfde catalogus behoren")

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        self.instance = serializer.instance

    def __call__(self, attrs: dict):
        default_deelzaaktypen = (
            self.instance.deelzaaktypen.all() if self.instance else []
        )
        default_catalogus = self.instance.catalogus if self.instance else None

        deelzaaktypen = attrs.get("deelzaaktypen") or default_deelzaaktypen
        catalogus = attrs.get("catalogus") or default_catalogus

        # can't run validator...
        if catalogus is None:
            return

        if any(
            deelzaaktype.catalogus_id != catalogus.id for deelzaaktype in deelzaaktypen
        ):
            raise ValidationError({"deelzaaktypen": self.message}, code=self.code)


class ConceptUpdateValidator:
    message = _("Het is niet toegestaan om een non-concept object bij te werken")
    code = "non-concept-object"

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)
        self.request = serializer.context["request"]

    def __call__(self, attrs):
        if not self.instance:
            return

        einde_geldigheid = attrs.get("datum_einde_geldigheid")
        if einde_geldigheid and len(self.request.data) == 1:
            return

        if not self.instance.concept:
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

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs):
        if self.instance:
            zaaktype = self.instance.zaaktype
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

    def __init__(self, concept_related_fields):
        self.concept_related_fields = concept_related_fields

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)

    def __call__(self, attrs):
        if self.instance:
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

    def __init__(self, concept_related_fields):
        self.concept_related_fields = concept_related_fields

    def set_context(self, serializer):
        """
        This hook is called by the serializer instance,
        prior to the validation call being made.
        """
        # Determine the existing instance, if this is an update operation.
        self.instance = getattr(serializer, "instance", None)
        self.request = serializer.context["request"]

    def __call__(self, attrs):
        if not self.instance:
            return

        einde_geldigheid = attrs.get("datum_einde_geldigheid")
        if einde_geldigheid and len(self.request.data) == 1:
            return

        for field_name in self.concept_related_fields:
            field = getattr(self.instance, field_name)
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
