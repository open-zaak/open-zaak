# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from rest_framework.test import APITestCase

from .factories import BestandsDeelFactory, EnkelvoudigInformatieObjectFactory


class UploadTestCase(APITestCase):
    def test_complete_upload_true(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        canonical = eio.canonical
        BestandsDeelFactory.create(informatieobject=canonical)

        self.assertTrue(canonical.complete_upload)

    def test_complete_upload_false(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        canonical = eio.canonical
        BestandsDeelFactory.create(informatieobject=canonical)
        BestandsDeelFactory.create(informatieobject=canonical, inhoud=None, omvang=0)

        self.assertFalse(canonical.complete_upload)

    def test_complete_part_true(self):
        part = BestandsDeelFactory.create()

        self.assertTrue(part.voltooid)

    def test_complete_part_false(self):
        part = BestandsDeelFactory.create(inhoud=None, omvang=0)

        self.assertFalse(part.voltooid)
