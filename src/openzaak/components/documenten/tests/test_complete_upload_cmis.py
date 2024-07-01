# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from io import BytesIO

from django.core.files import File
from django.test import override_settings

from openzaak.components.documenten.models import BestandsDeel
from openzaak.tests.utils import APICMISTestCase, require_cmis

from .factories import BestandsDeelFactory, EnkelvoudigInformatieObjectFactory


@require_cmis
@override_settings(
    DOCUMENTEN_UPLOAD_CHUNK_SIZE=10,
    CMIS_ENABLED=True,
)
class UploadTestCase(APICMISTestCase):
    def test_complete_upload_true(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        BestandsDeelFactory.create(
            informatieobject=None, informatieobject_uuid=eio.uuid
        )

        self.assertTrue(
            BestandsDeel.objects.filter(informatieobject_uuid=eio.uuid).complete_upload
        )

    def test_complete_upload_false(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        BestandsDeelFactory.create(
            informatieobject=None, informatieobject_uuid=eio.uuid
        )
        BestandsDeelFactory.create(
            informatieobject=None, informatieobject_uuid=eio.uuid, inhoud=None, omvang=9
        )

        self.assertFalse(
            BestandsDeel.objects.filter(informatieobject_uuid=eio.uuid).complete_upload
        )

    def test_complete_part_true(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        part = BestandsDeelFactory.create(
            informatieobject=None, informatieobject_uuid=eio.uuid
        )

        self.assertTrue(part.voltooid)

    def test_complete_part_false_no_file_uploaded(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        part = BestandsDeelFactory.create(
            informatieobject=None, informatieobject_uuid=eio.uuid, inhoud=None, omvang=9
        )

        self.assertFalse(part.voltooid)

    def test_complete_part_false_file_size_mismatch(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        part = BestandsDeelFactory.create(
            informatieobject=None,
            informatieobject_uuid=eio.uuid,
            inhoud=File(BytesIO(b"12345678"), name="somefile"),
            omvang=9,
        )

        self.assertFalse(part.voltooid)
