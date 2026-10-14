# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.core.exceptions import ValidationError
from django.test import TestCase

from ..models import ResultaatType, StatusType
from ..models.validators import is_referentiecode_in_use
from .factories import ResultaatTypeFactory, StatusTypeFactory, ZaakTypeFactory


def _new_version(zaaktype):
    return ZaakTypeFactory.create(
        concept=True,
        catalogus=zaaktype.catalogus,
        identificatie=zaaktype.identificatie,
    )


class ResultaatTypeReferentiecodeCleanTests(TestCase):
    def test_same_code_other_zaaktype_family_not_allowed(self):
        ResultaatTypeFactory.create(omschrijving="bestaand", referentiecode="A1")
        resultaattype = ResultaatTypeFactory.build(
            zaaktype=ZaakTypeFactory.create(concept=True),
            omschrijving="bestaand",
            referentiecode="A1",
        )

        with self.assertRaises(ValidationError) as cm:
            resultaattype.clean()

        self.assertIn("referentiecode", cm.exception.message_dict)

    def test_same_code_same_resultaattype_in_new_version_allowed(self):
        old = ResultaatTypeFactory.create(omschrijving="bestaand", referentiecode="A1")
        resultaattype = ResultaatTypeFactory.build(
            zaaktype=_new_version(old.zaaktype),
            omschrijving="bestaand",
            referentiecode="A1",
        )

        resultaattype.clean()

    def test_same_code_other_resultaattype_in_new_version_not_allowed(self):
        old = ResultaatTypeFactory.create(omschrijving="bestaand", referentiecode="A1")
        resultaattype = ResultaatTypeFactory.build(
            zaaktype=_new_version(old.zaaktype),
            omschrijving="ander",
            referentiecode="A1",
        )

        with self.assertRaises(ValidationError) as cm:
            resultaattype.clean()

        self.assertIn("referentiecode", cm.exception.message_dict)

    def test_other_resultaattype_in_same_zaaktype_not_allowed(self):
        old = ResultaatTypeFactory.create(omschrijving="bestaand", referentiecode="A1")
        resultaattype = ResultaatTypeFactory.build(
            zaaktype=old.zaaktype, omschrijving="ander", referentiecode="A1"
        )

        with self.assertRaises(ValidationError):
            resultaattype.clean()

    def test_saved_resultaattype_keeps_own_code(self):
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__concept=True, referentiecode="A1"
        )

        resultaattype.clean()

    def test_empty_code_is_ignored(self):
        ResultaatTypeFactory.create(omschrijving="bestaand", referentiecode=None)
        resultaattype = ResultaatTypeFactory.build(
            zaaktype=ZaakTypeFactory.create(concept=True),
            omschrijving="bestaand",
            referentiecode=None,
        )

        resultaattype.clean()


class IsReferentiecodeInUseTests(TestCase):
    def test_no_code(self):
        statustype = StatusTypeFactory.create(referentiecode="A1")

        for code in (None, ""):
            with self.subTest(code=code):
                self.assertFalse(
                    is_referentiecode_in_use(
                        StatusType,
                        zaaktype=statustype.zaaktype,
                        referentiecode=code,
                        identity_field="statustypevolgnummer",
                        identity_value=99,
                    )
                )

    def test_own_object_is_excluded_by_pk(self):
        statustype = StatusTypeFactory.create(referentiecode="A1")

        self.assertFalse(
            is_referentiecode_in_use(
                StatusType,
                zaaktype=statustype.zaaktype,
                referentiecode="A1",
                identity_field="statustypevolgnummer",
                identity_value=statustype.statustypevolgnummer,
                pk=statustype.pk,
            )
        )

    def test_same_identity_in_other_version_is_excluded(self):
        statustype = StatusTypeFactory.create(referentiecode="A1")

        self.assertFalse(
            is_referentiecode_in_use(
                StatusType,
                zaaktype=_new_version(statustype.zaaktype),
                referentiecode="A1",
                identity_field="statustypevolgnummer",
                identity_value=statustype.statustypevolgnummer,
            )
        )

    def test_other_identity_in_same_family_is_in_use(self):
        statustype = StatusTypeFactory.create(referentiecode="A1")

        self.assertTrue(
            is_referentiecode_in_use(
                StatusType,
                zaaktype=_new_version(statustype.zaaktype),
                referentiecode="A1",
                identity_field="statustypevolgnummer",
                identity_value=statustype.statustypevolgnummer + 1,
            )
        )

    def test_other_family_is_in_use(self):
        statustype = StatusTypeFactory.create(referentiecode="A1")

        self.assertTrue(
            is_referentiecode_in_use(
                StatusType,
                zaaktype=ZaakTypeFactory.create(),
                referentiecode="A1",
                identity_field="statustypevolgnummer",
                identity_value=statustype.statustypevolgnummer,
            )
        )

    def test_models_are_checked_separately(self):
        ResultaatTypeFactory.create(referentiecode="A1")

        self.assertFalse(
            is_referentiecode_in_use(
                StatusType,
                zaaktype=ZaakTypeFactory.create(),
                referentiecode="A1",
                identity_field="statustypevolgnummer",
                identity_value=1,
            )
        )
        self.assertIs(ResultaatType.objects.filter(referentiecode="A1").exists(), True)
