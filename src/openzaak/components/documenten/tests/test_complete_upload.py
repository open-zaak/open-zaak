# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from io import BytesIO

from django.core.files import File

from rest_framework.test import APITestCase

from openzaak.components.documenten.models import BestandsDeel

from .factories import BestandsDeelFactory, EnkelvoudigInformatieObjectFactory


class UploadTestCase(APITestCase):
    def test_complete_upload_true(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        canonical = eio.canonical
        BestandsDeelFactory.create(informatieobject=canonical)

        self.assertTrue(
            BestandsDeel.objects.filter(informatieobject=canonical).complete_upload
        )

    def test_complete_upload_false(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        canonical = eio.canonical
        BestandsDeelFactory.create(informatieobject=canonical)
        BestandsDeelFactory.create(informatieobject=canonical, inhoud=None, omvang=9)

        self.assertFalse(
            BestandsDeel.objects.filter(informatieobject=canonical).complete_upload
        )

    def test_complete_part_true(self):
        part = BestandsDeelFactory.create()

        self.assertTrue(part.voltooid)

    def test_complete_part_false_no_file_uploaded(self):
        part = BestandsDeelFactory.create(inhoud=None, omvang=9)

        self.assertFalse(part.voltooid)

    def test_complete_part_false_file_size_mismatch(self):
        part = BestandsDeelFactory.create(
            inhoud=File(BytesIO(b"12345678"), name="somefile"), omvang=9
        )

        self.assertFalse(part.voltooid)
