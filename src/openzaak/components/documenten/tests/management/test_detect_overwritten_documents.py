# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import hashlib
import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from privates.test import temp_private_root

from ...models import EnkelvoudigInformatieObject
from ..factories import (
    BestandsDeelFactory,
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)

AFFECTED = {"shared-file", "wrong-size", "wrong-hash"}


def create_document(**kwargs) -> EnkelvoudigInformatieObject:
    # a unique bestandsnaam, unless the test is about the same bestandsnaam
    kwargs.setdefault("bestandsnaam", f"{uuid4().hex}.pdf")
    return EnkelvoudigInformatieObjectFactory.create(**kwargs)


def registered(document: EnkelvoudigInformatieObject, at):
    # begin_registratie is auto_now, a queryset update doesn't touch it
    EnkelvoudigInformatieObject.objects.filter(pk=document.pk).update(
        begin_registratie=at
    )


@temp_private_root()
class DetectOverwrittenDocumentsTests(TestCase):
    def call_command(self, *args) -> tuple[list[list[str]], str]:
        stdout, stderr = StringIO(), StringIO()
        call_command(
            "detect_overwritten_documents", *args, stdout=stdout, stderr=stderr
        )
        header, *lines = stdout.getvalue().splitlines()
        self.assertEqual(header, "strength\tcheck\tuuid\tversie\tdetail")
        rows = [line.split("\t") for line in lines]
        for row in rows:
            self.assertEqual(len(row), 5, row)
            strength, check, *_ = row
            if check in AFFECTED:
                self.assertEqual(strength, "affected", check)
            else:
                self.assertIn(strength, ["possible", "unlikely"], check)
        return rows, stderr.getvalue()

    def detect(self, *args) -> set[tuple[str, str]]:
        rows, _ = self.call_command(*args)
        return {(check, uuid) for _, check, uuid, *_ in rows}

    def strengths(self, *args) -> dict[str, str]:
        rows, _ = self.call_command(*args)
        return {uuid: strength for strength, _, uuid, *_ in rows}

    def test_nothing_to_report(self):
        document = create_document()
        # a new version of the same document shares its file
        create_document(
            canonical=document.canonical,
            versie=2,
            bestandsnaam=document.bestandsnaam,
            inhoud=document.inhoud.name,
            bestandsomvang=document.bestandsomvang,
        )

        self.assertEqual(self.detect("--verify-integrity"), set())

    def test_different_documents_sharing_a_file(self):
        first = create_document()
        second = create_document(
            inhoud=first.inhoud.name, bestandsomvang=first.bestandsomvang
        )

        self.assertEqual(
            self.detect(),
            {("shared-file", str(first.uuid)), ("shared-file", str(second.uuid))},
        )

    def test_absolute_path_from_import_sharing_a_file(self):
        # short name: `inhoud` is limited to 100 characters, including the location
        uploaded = create_document(inhoud__filename="b.pdf")
        imported = create_document(
            inhoud=f"{settings.PRIVATE_MEDIA_ROOT}/{uploaded.inhoud.name}",
            bestandsomvang=uploaded.bestandsomvang,
        )

        self.assertEqual(
            self.detect(),
            {("shared-file", str(uploaded.uuid)), ("shared-file", str(imported.uuid))},
        )

    def test_size_differs_from_bestandsomvang(self):
        document = create_document(bestandsomvang=1234)

        self.assertEqual(self.detect(), {("wrong-size", str(document.uuid))})

    def test_missing_file(self):
        document = create_document()
        assert document.inhoud.name
        document.inhoud.storage.delete(document.inhoud.name)

        self.assertEqual(self.detect(), {("missing-file", str(document.uuid))})

    def test_integrity_mismatch(self):
        content = b"some data"
        matching = create_document(
            inhoud__data=content,
            integriteit_algoritme="sha_256",
            integriteit_waarde=hashlib.sha256(content).hexdigest(),
        )
        mismatching = create_document(
            inhoud__data=content,
            integriteit_algoritme="sha_256",
            integriteit_waarde=hashlib.sha256(b"other data").hexdigest(),
        )

        with self.subTest("only with --verify-integrity"):
            self.assertEqual(self.detect(), set())

        findings = self.detect("--verify-integrity")

        self.assertIn(("wrong-hash", str(mismatching.uuid)), findings)
        self.assertNotIn(("wrong-hash", str(matching.uuid)), findings)

    def test_same_bestandsnaam_without_hash_is_possible(self):
        first = create_document(bestandsnaam="besluit.pdf")
        second = create_document(bestandsnaam="besluit.pdf")

        self.assertEqual(
            self.detect(),
            {("same-name", str(first.uuid)), ("same-name", str(second.uuid))},
        )

    def test_same_bestandsnaam_verified_by_hash(self):
        documents = [
            create_document(
                bestandsnaam="besluit.pdf",
                inhoud__data=content,
                integriteit_algoritme="sha_256",
                integriteit_waarde=hashlib.sha256(content).hexdigest(),
            )
            for content in [b"first", b"second"]
        ]

        with self.subTest("only with --verify-integrity"):
            self.assertEqual(
                self.detect(), {("same-name", str(d.uuid)) for d in documents}
            )

        self.assertEqual(self.detect("--verify-integrity"), set())

    def test_same_merge_file_name_for_different_bestandsnaam(self):
        # without an extension, `.bin` is added; spaces become underscores
        pairs = [("besluit", "besluit.bin"), ("bijlage 1.pdf", "bijlage_1.pdf")]
        for names in pairs:
            with self.subTest(names):
                documents = [create_document(bestandsnaam=name) for name in names]

                findings = self.detect()

                for document in documents:
                    self.assertIn(("same-name", str(document.uuid)), findings)

    def test_document_without_inhoud_counts_as_same_bestandsnaam(self):
        # the unlock that overwrote this document's content failed itself
        overwritten = create_document(bestandsnaam="besluit.pdf")
        create_document(bestandsnaam="besluit.pdf", inhoud=None, bestandsomvang=9)

        self.assertEqual(self.detect(), {("same-name", str(overwritten.uuid))})

    def test_quick_only_checks_same_bestandsnaam(self):
        unique = create_document(bestandsomvang=1234)
        same = [
            create_document(bestandsnaam="besluit.pdf", bestandsomvang=1234)
            for _ in range(2)
        ]

        self.assertEqual(
            self.detect("--quick"), {("wrong-size", str(d.uuid)) for d in same}
        )
        self.assertEqual(
            self.detect(), {("wrong-size", str(d.uuid)) for d in [unique, *same]}
        )

    def test_same_name_unlocked_far_apart_is_unlikely(self):
        now = timezone.now()
        first = create_document(bestandsnaam="besluit.pdf")
        second = create_document(bestandsnaam="besluit.pdf")
        registered(first, now - timedelta(days=1))
        registered(second, now)

        self.assertEqual(
            self.strengths(),
            {str(first.uuid): "unlikely", str(second.uuid): "unlikely"},
        )

    def test_same_name_unlocked_within_the_window_is_possible(self):
        now = timezone.now()
        first = create_document(bestandsnaam="besluit.pdf")
        second = create_document(bestandsnaam="besluit.pdf")
        registered(first, now - timedelta(seconds=10))
        registered(second, now)

        self.assertEqual(
            self.strengths(),
            {str(first.uuid): "possible", str(second.uuid): "possible"},
        )

    def test_window_is_size_over_throughput_plus_margin(self):
        now = timezone.now()
        first = create_document(bestandsnaam="besluit.pdf")  # 9 bytes
        second = create_document(bestandsnaam="besluit.pdf")
        registered(first, now - timedelta(seconds=5))
        registered(second, now)

        cases = [
            # 9 bytes at ~1 byte/s take ~9 s: 5 s apart can overlap
            (["--min-throughput", "0.001", "--margin", "0"], "possible"),
            # 9 bytes at 256 KiB/s take no time: 5 s apart can't overlap
            (["--margin", "0"], "unlikely"),
            # unless the margin covers it
            (["--margin", "6"], "possible"),
        ]
        for options, strength in cases:
            with self.subTest(options):
                self.assertEqual(self.strengths(*options)[str(first.uuid)], strength)

    def test_failed_unlock_of_a_namesake_happened_at_an_unknown_time(self):
        now = timezone.now()
        overwritten = create_document(bestandsnaam="besluit.pdf")
        failed = create_document(
            bestandsnaam="besluit.pdf", inhoud=None, bestandsomvang=9
        )
        registered(overwritten, now)

        with self.subTest("it failed after this one was saved"):
            registered(failed, now - timedelta(days=1))
            self.assertEqual(self.strengths()[str(overwritten.uuid)], "possible")

        with self.subTest("it was created after this one was unlocked"):
            registered(failed, now + timedelta(days=1))
            self.assertEqual(self.strengths()[str(overwritten.uuid)], "unlikely")

    def test_document_edited_in_the_admin_has_an_unreliable_time(self):
        now = timezone.now()
        edited = create_document(bestandsnaam="besluit.pdf")
        other = create_document(bestandsnaam="besluit.pdf")
        registered(edited, now - timedelta(days=1))
        registered(other, now)
        LogEntry.objects.create(
            user=get_user_model().objects.create(username="admin"),
            content_type=ContentType.objects.get_for_model(EnkelvoudigInformatieObject),
            object_id=str(edited.pk),
            object_repr=str(edited),
            action_flag=CHANGE,
        )

        self.assertEqual(
            self.strengths(),
            {str(edited.uuid): "possible", str(other.uuid): "possible"},
        )

    def test_failed_unlock_without_content(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__inhoud=None, latest_version__bestandsomvang=18
        )
        BestandsDeelFactory.create_batch(2, informatieobject=canonical)
        failed = canonical.latest_version
        assert isinstance(failed, EnkelvoudigInformatieObject)

        with self.subTest("still locked: the upload isn't finished"):
            canonical.lock = "locked"
            canonical.save()
            self.assertEqual(self.detect(), set())

        canonical.lock = ""
        canonical.save()

        self.assertEqual(self.detect(), {("no-content", str(failed.uuid))})

    def test_size_unknown_without_namesake(self):
        document = create_document(bestandsomvang=None)

        self.assertEqual(self.strengths(), {str(document.uuid): "unlikely"})
        self.assertEqual(self.detect(), {("size-unknown", str(document.uuid))})

    def test_absolute_path_after_the_storage_location_moved(self):
        uploaded = create_document(inhoud__filename="b.pdf")
        imported = create_document(
            inhoud=f"/old/private-media/{uploaded.inhoud.name}",
            bestandsomvang=uploaded.bestandsomvang,
        )

        self.assertEqual(
            self.detect(),
            {("shared-file", str(uploaded.uuid)), ("shared-file", str(imported.uuid))},
        )

    def test_storage_errors_are_reported_and_the_run_finishes(self):
        document = create_document()
        storage = document.inhoud.storage

        with (
            patch.object(storage, "size", side_effect=PermissionError("403")),
            patch.object(storage, "exists", side_effect=PermissionError("403")),
        ):
            rows, summary = self.call_command()

        self.assertEqual(
            {(row[1], row[2]) for row in rows}, {("not-checked", str(document.uuid))}
        )
        self.assertIn("Possible: 1", summary)

    def test_file_names_are_escaped(self):
        document = create_document(
            inhoud="uploads/2024/01/a\tb\nc.pdf", bestandsomvang=9
        )

        rows, _ = self.call_command()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1:3], ["missing-file", str(document.uuid)])
        self.assertIn("a\\tb\\nc.pdf", rows[0][4])

    def test_jsonl_has_the_evidence(self):
        now = timezone.now()
        first = create_document(bestandsnaam="besluit.pdf")
        second = create_document(bestandsnaam="besluit.pdf")
        registered(first, now - timedelta(seconds=10))
        registered(second, now)
        stdout = StringIO()

        call_command(
            "detect_overwritten_documents",
            "--format",
            "jsonl",
            stdout=stdout,
            stderr=StringIO(),
        )

        findings = [json.loads(line) for line in stdout.getvalue().splitlines()]
        finding = next(f for f in findings if f["uuid"] == str(first.uuid))
        self.assertEqual(finding["check"], "same-name")
        self.assertEqual(finding["evidence"]["namesakes"], 1)
        [overlap] = finding["evidence"]["overlaps"]
        self.assertEqual(overlap["uuid"], str(second.uuid))
        self.assertEqual(overlap["delta_seconds"], -10)

    def test_summary_has_background_rates(self):
        create_document(bestandsomvang=1234)
        create_document()

        _, summary = self.call_command()

        self.assertIn("Affected: 1 (1 wrong-size)", summary)
        self.assertIn("wrong-size: 0/0", summary.replace("none checked", "0/0"))

    def test_is_read_only(self):
        first = create_document(bestandsomvang=1234)
        create_document(inhoud=first.inhoud.name, bestandsomvang=first.bestandsomvang)
        storage = first.inhoud.storage
        storage.save("unrelated.txt", ContentFile(b"x"))
        before = list(EnkelvoudigInformatieObject.objects.values().order_by("pk"))

        self.detect("--verify-integrity")

        self.assertEqual(
            list(EnkelvoudigInformatieObject.objects.values().order_by("pk")), before
        )
        assert first.inhoud.name
        self.assertTrue(storage.exists(first.inhoud.name))
        self.assertTrue(storage.exists("unrelated.txt"))
