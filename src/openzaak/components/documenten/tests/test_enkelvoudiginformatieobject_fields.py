# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import SimpleTestCase

from django_loose_fk.virtual_models import get_model_instance

from ..api.fields import EnkelvoudigInformatieObjectField
from ..models import EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical


class EnkelvoudigInformatieObjectFieldsTests(SimpleTestCase):
    def test_inclusion_uses_latest_version(self):
        document = EnkelvoudigInformatieObject(versie=2)
        canonical = EnkelvoudigInformatieObjectCanonical(latest_version=document)

        self.assertIs(
            EnkelvoudigInformatieObjectField().get_inclusion_instance(canonical),
            document,
        )

    def test_inclusion_preserves_remote_document(self):
        document = get_model_instance(
            EnkelvoudigInformatieObject,
            {
                "url": "https://documenten.example.com/documenten/1",
                "bestandsnaam": "report.pdf",
            },
            loader=None,
        )

        self.assertIs(
            EnkelvoudigInformatieObjectField().get_inclusion_instance(document),
            document,
        )

    def test_inclusion_without_document(self):
        self.assertIsNone(
            EnkelvoudigInformatieObjectField().get_inclusion_instance(None)
        )
