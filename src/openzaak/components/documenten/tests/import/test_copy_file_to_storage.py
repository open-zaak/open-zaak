# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.test import override_settings

from hypothesis import example, given, strategies as st
from hypothesis.extra.django import SimpleTestCase

from openzaak.components.documenten.constants import DocumentenBackendTypes
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.tasks import copy_file_to_storage
from openzaak.utils.fields import get_default_path

# Anything a single path component can hold; kept short enough to fit the 255 byte
# limit of most filesystems after a storage appends a random suffix.
file_names = st.text(
    st.characters(blacklist_categories=["Cs"], blacklist_characters="/\x00"),
    min_size=1,
    max_size=50,
).filter(lambda name: name not in {".", ".."})

# bulk import names that may not be unique (often aren't)
bulk_file_names = st.lists(file_names, min_size=1, max_size=3).flatmap(
    lambda pool: st.lists(st.sampled_from(pool), min_size=2, max_size=6)
)


class CopyFileToFilesystemStorageTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

        storages = {
            **settings.STORAGES,
            "privates": {
                **settings.STORAGES["privates"],
                "OPTIONS": {
                    **settings.STORAGES["privates"].get("OPTIONS", {}),
                    "location": self.tmp / "private-media",
                },
            },
        }
        overrides = override_settings(
            STORAGES=storages,
            DOCUMENTEN_API_BACKEND=DocumentenBackendTypes.filesystem,
        )
        overrides.enable()
        self.addCleanup(overrides.disable)

    @given(names=bulk_file_names)
    @example(names=["besluit.pdf", "besluit.pdf"])
    # bestandspad is a path; the same name in different directories
    @example(names=["a/besluit.pdf", "b/besluit.pdf"])
    @example(names=["a/b.pdf", "b.pdf"])
    # on POSIX a backslash is part of the file name, but storages treat it as a
    # path separator
    @example(names=["\\", "\\"])
    @example(names=[r"a\b.pdf", r"a\b.pdf", "a/b.pdf"])
    @example(names=[r"..\besluit.pdf", "../besluit.pdf"])
    def test_files_with_the_same_name_do_not_overwrite_each_other(self, names):
        with TemporaryDirectory(dir=self.tmp) as import_dir:
            sources = []
            for i, name in enumerate(names):
                # import rows can point to files in different subdirectories
                src = Path(import_dir) / str(i) / name
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_bytes(str(i).encode())
                sources.append(src)

            # mirror _import_document_row
            default_dir = get_default_path(EnkelvoudigInformatieObject.inhoud.field)
            stored = {}
            for i, src in enumerate(sources):
                try:
                    stored[i] = copy_file_to_storage(src, default_dir / src.name)
                except SuspiciousFileOperation:
                    # the storage rejects names like `\` or `..\besluit.pdf`; the
                    # import reports these rows as failed
                    self.assertIn("\N{REVERSE SOLIDUS}", src.name)

            self.assertEqual(len(set(stored.values())), len(stored))
            storage = EnkelvoudigInformatieObject.inhoud.field.storage
            for i, name in stored.items():
                with storage.open(name, "rb") as f:
                    self.assertEqual(f.read(), str(i).encode())
