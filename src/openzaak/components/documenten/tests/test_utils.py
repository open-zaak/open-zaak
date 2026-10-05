# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from io import BytesIO

from django.core.files.base import ContentFile

from hypothesis import given, strategies as st
from hypothesis.extra.django import SimpleTestCase

from openzaak.components.documenten.api.utils import merge_files


class MergeFilesTests(SimpleTestCase):
    @given(parts=st.lists(st.binary()))
    def test_merges_parts_in_order(self, parts):
        dst = BytesIO()

        merge_files(map(ContentFile, parts), dst)

        self.assertEqual(dst.getvalue(), b"".join(parts))
