# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
"""
Report documents whose content may have been overwritten or lost by #2592.

The reasoning, the assumptions and how they can fail are documented in
``docs/installation/reference/overwritten_documents.rst``; keep both in sync.
"""

import base64
import bisect
import hashlib
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import Storage
from django.core.management import BaseCommand
from django.db.models import CharField, Count, Exists, F, Func, OuterRef, Value

from openzaak.components.documenten.api.utils import create_filename
from openzaak.components.documenten.models import (
    BestandsDeel,
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)

HASHES = {
    "md5": hashlib.md5,
    "sha_1": hashlib.sha1,
    "sha_256": hashlib.sha256,
    "sha_512": hashlib.sha512,
}

# how strongly a finding points to lost content; alphabetical, so `sort` works
AFFECTED, POSSIBLE, UNLIKELY = "affected", "possible", "unlikely"
STRENGTHS = [AFFECTED, POSSIBLE, UNLIKELY]

# Bulk imports on filesystem storage stored absolute paths. The storage location may
# have moved since, so they're normalized by their upload path, not the location.
UPLOAD_PATH = "uploads/[0-9]{4}/[0-9]{2}/[^/]+"
ABSOLUTE_UPLOAD = re.compile(f"^/.*/({UPLOAD_PATH})$")


@dataclass
class Finding:
    strength: str
    check: str
    uuid: str
    versie: int
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Version:
    """A version of a document, as far as the timing model is concerned."""

    pk: int
    uuid: str
    versie: int
    canonical: int
    has_content: bool
    bestandsomvang: int | None
    # auto_now: set by the last save of this version; for a version that got its
    # content by an unlock, that's right after the merged file was stored
    begin_registratie: datetime


@dataclass(frozen=True)
class Timing:
    """
    Assumptions about how long an unlock took to merge and store a document.
    """

    min_throughput: float  # bytes per second, merging and storing together
    margin: float  # seconds: request overhead and clock skew between servers

    def window(self, *sizes: int) -> float:
        """
        Two unlocks can only have overlapped if their begin_registratie differ by
        less than this.
        """
        return max(sizes) / self.min_throughput + self.margin


def get_storage() -> Storage:
    return EnkelvoudigInformatieObject._meta.get_field("inhoud").storage  # pyright: ignore[reportAttributeAccessIssue]


def normalize(name: str) -> str:
    match = ABSOLUTE_UPLOAD.match(name)
    return match.group(1) if match else name


def escape(value: str) -> str:
    """Keep each finding on one tab separated line; file names may contain both."""
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval of a proportion."""
    if not total:
        return 0.0, 1.0
    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    spread = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return max(0.0, centre - spread), min(1.0, centre + spread)


@cache
def merge_key(bestandsnaam: str) -> str | None:
    """
    Unlocking merged the bestandsdelen in ``PRIVATE_MEDIA_ROOT/<name>``, with the name
    derived from the bestandsnaam like this. Documents with the same name could get
    each other's content.

    The key is deliberately coarse: it may group too many documents, never too few.
    """
    inhoud = EnkelvoudigInformatieObject._meta.get_field("inhoud")
    try:
        name = Path(
            inhoud.generate_filename(None, create_filename(bestandsnaam))  # pyright: ignore[reportAttributeAccessIssue]
        ).name
    except Exception:
        return None  # the unlock failed before merging
    return "".join(c for c in name.lower() if c.isalnum())


def find_namesakes() -> dict[str, list[Version]]:
    """
    Versions of documents grouped by merge key, for keys shared by different
    documents. Documents without inhoud count too: the unlock that overwrote another
    document's content may have failed itself.
    """
    groups: dict[str, list[Version]] = defaultdict(list)
    for row in (
        EnkelvoudigInformatieObject.objects.order_by()
        .values_list(
            "pk",
            "uuid",
            "versie",
            "canonical",
            "inhoud",
            "bestandsomvang",
            "begin_registratie",
            "bestandsnaam",
        )
        .iterator()
    ):
        key = merge_key(row[-1])
        if key is not None:
            pk, uuid, versie, canonical, inhoud, bestandsomvang, registratie = row[:-1]
            groups[key].append(
                Version(
                    pk,
                    str(uuid),
                    versie,
                    canonical,
                    bool(inhoud),
                    bestandsomvang,
                    registratie,
                )
            )
    return {
        key: versions
        for key, versions in groups.items()
        if len({v.canonical for v in versions}) > 1
    }


def find_edited_in_admin() -> set[int]:
    """
    Versions that may have been saved after their unlock, moving begin_registratie.
    """
    log = LogEntry.objects.filter(action_flag=CHANGE)
    eio_type = ContentType.objects.get_for_model(EnkelvoudigInformatieObject)
    canonical_type = ContentType.objects.get_for_model(
        EnkelvoudigInformatieObjectCanonical
    )
    edited = {
        int(pk)
        for pk in log.filter(content_type=eio_type).values_list("object_id", flat=True)
        if pk.isdigit()
    }
    # versions can be edited inline on their canonical
    canonicals = {
        int(pk)
        for pk in log.filter(content_type=canonical_type).values_list(
            "object_id", flat=True
        )
        if pk.isdigit()
    }
    edited.update(
        EnkelvoudigInformatieObject.objects.filter(
            canonical__in=canonicals
        ).values_list("pk", flat=True)
    )
    return edited


class NamesakeGroup:
    """
    Documents with the same merge key, to assess whether their unlocks could have
    overlapped in time.
    """

    # evidence lists are capped, the counts are not
    MAX_EVIDENCE = 20

    def __init__(self, versions: list[Version], edited: set[int], timing: Timing):
        self.timing = timing
        self.edited = edited
        self.by_pk = {v.pk: v for v in versions}
        self.canonicals = Counter(v.canonical for v in versions)
        # namesakes whose overlap can't be bounded in time at all
        self.unbounded = [
            v
            for v in versions
            if v.pk in edited or (v.has_content and v.bestandsomvang is None)
        ]
        # unlock failed, at an unknown time after their last save
        self.failed = sorted(
            (v for v in versions if not v.has_content and v.bestandsomvang),
            key=lambda v: v.begin_registratie,
        )
        # the rest: content with a known size, overlap bounded by the window
        self.bounded = sorted(
            (
                v
                for v in versions
                if v.has_content and v.bestandsomvang is not None and v.pk not in edited
            ),
            key=lambda v: v.begin_registratie,
        )
        self.bounded_times = [v.begin_registratie.timestamp() for v in self.bounded]
        self.max_size = max((v.bestandsomvang or 0 for v in self.bounded), default=0)

    def entry(self, version: Version, other: Version, **extra) -> dict:
        return {
            "uuid": other.uuid,
            "versie": other.versie,
            "begin_registratie": other.begin_registratie,
            "bestandsomvang": other.bestandsomvang,
            "has_content": other.has_content,
            "delta_seconds": (
                version.begin_registratie - other.begin_registratie
            ).total_seconds(),
            **extra,
        }

    def assess(self, pk: int) -> tuple[str, float, dict]:
        """
        Could the unlock of a document with the same name have overlapped with the
        unlock of this version? Returns the strength, the time to the nearest
        namesake and the evidence.
        """
        version = self.by_pk[pk]
        evidence: dict = {
            "begin_registratie": version.begin_registratie,
            # other documents, not versions
            "namesakes": len(self.canonicals) - 1,
        }
        if version.pk in self.edited:
            evidence["reason"] = "edited in the admin, begin_registratie may have moved"
            return POSSIBLE, 0.0, evidence
        if version.bestandsomvang is None:
            evidence["reason"] = "no bestandsomvang, the merge time is unknown"
            return POSSIBLE, 0.0, evidence

        def others(versions):
            return (v for v in versions if v.canonical != version.canonical)

        overlapping = [
            self.entry(version, other, overlap="unknown: edited or no bestandsomvang")
            for other in others(self.unbounded)
        ]
        # a failed unlock happened after its last save, so only a version that was
        # unlocked before that is ruled out
        latest = version.begin_registratie.timestamp() + self.timing.margin
        for other in others(self.failed):
            if other.begin_registratie.timestamp() > latest:
                break
            overlapping.append(
                self.entry(version, other, overlap="unknown: its unlock failed")
            )

        # only bounded namesakes within the largest possible window can overlap
        time = version.begin_registratie.timestamp()
        widest = self.timing.window(version.bestandsomvang, self.max_size)
        low = bisect.bisect_left(self.bounded_times, time - widest)
        high = bisect.bisect_right(self.bounded_times, time + widest)
        for other in others(self.bounded[low:high]):
            assert other.bestandsomvang is not None
            window = self.timing.window(version.bestandsomvang, other.bestandsomvang)
            entry = self.entry(version, other, window_seconds=window)
            if abs(entry["delta_seconds"]) < window:
                overlapping.append(entry | {"overlap": "possible: within the window"})

        evidence["overlapping"] = len(overlapping)
        if overlapping:
            nearest = min(abs(e["delta_seconds"]) for e in overlapping)
            evidence["overlaps"] = sorted(
                overlapping, key=lambda e: abs(e["delta_seconds"])
            )[: self.MAX_EVIDENCE]
            return POSSIBLE, nearest, evidence

        # all bounded namesakes are outside their window: report the nearest ones
        nearby = list(others(self.bounded[max(0, low - 5) : high + 5]))
        if not nearby:  # all namesakes are further away, find the nearest
            index = bisect.bisect_left(self.bounded_times, time)
            nearby = [
                v
                for v in self.bounded[max(0, index - 50) : index + 50]
                if v.canonical != version.canonical
            ]
        outside = sorted(
            (
                self.entry(
                    version,
                    other,
                    window_seconds=self.timing.window(
                        version.bestandsomvang, other.bestandsomvang or 0
                    ),
                )
                for other in nearby
            ),
            key=lambda e: abs(e["delta_seconds"]),
        )
        evidence["nearest_outside"] = outside[:5]
        nearest = abs(outside[0]["delta_seconds"]) if outside else math.inf
        return UNLIKELY, nearest, evidence


def describe_overlap(strength: str, nearest: float, evidence: dict) -> str:
    if "reason" in evidence:
        return evidence["reason"]
    if strength == POSSIBLE:
        return (
            f"{evidence['overlapping']} of {evidence['namesakes']} documents with the "
            f"same name may have been unlocked at the same time, nearest "
            f"{format_seconds(nearest)} apart"
        )
    outside = evidence["nearest_outside"]
    if not outside:
        return (
            f"{evidence['namesakes']} documents with the same name, none unlocked "
            "near this one"
        )
    return (
        f"{evidence['namesakes']} documents with the same name, nearest "
        f"{format_seconds(nearest)} apart, window "
        f"{format_seconds(outside[0]['window_seconds'])}"
    )


def format_seconds(seconds: float) -> str:
    for unit, size in [("d", 86400), ("h", 3600), ("min", 60)]:
        if seconds >= size:
            return f"{seconds / size:.1f} {unit}"
    return f"{seconds:.0f} s"


def find_shared_files() -> Iterator[Finding]:
    """
    Different documents pointing to the same file; at most one of them can have its
    own content. (Versions of the same document legitimately share a file.)
    """
    documents = EnkelvoudigInformatieObject.objects.exclude(inhoud="").annotate(
        name=Func(
            F("inhoud"),
            Value(ABSOLUTE_UPLOAD.pattern),
            Value(r"\1"),
            function="regexp_replace",
            output_field=CharField(),
        )
    )
    shared = (
        documents.values("name")
        .annotate(canonicals=Count("canonical", distinct=True))
        .filter(canonicals__gt=1)
        .values("name")
    )
    for document in (
        documents.filter(name__in=shared)
        .order_by("name", "canonical", "versie")
        .values("uuid", "versie", "name")
        .iterator()
    ):
        yield Finding(
            AFFECTED,
            "shared-file",
            str(document["uuid"]),
            document["versie"],
            document["name"],
            {"file": document["name"]},
        )


def find_failed_unlocks() -> Iterator[Finding]:
    """
    Unlocked documents without content whose bestandsdelen were all uploaded: the
    unlock failed while merging them. The content is still in the bestandsdelen.
    """
    canonicals = (
        EnkelvoudigInformatieObjectCanonical.objects.filter(
            lock="",
            latest_version__inhoud="",
            latest_version__bestandsomvang__gt=0,
        )
        .filter(Exists(BestandsDeel.objects.filter(informatieobject=OuterRef("pk"))))
        .exclude(
            Exists(
                BestandsDeel.objects.filter(informatieobject=OuterRef("pk"), inhoud="")
            )
        )
        .values("latest_version__uuid", "latest_version__versie")
    )
    for canonical in canonicals.iterator():
        yield Finding(
            POSSIBLE,
            "no-content",
            str(canonical["latest_version__uuid"]),
            canonical["latest_version__versie"],
            "unlocked without inhoud; the bestandsdelen are still there",
        )


def hash_matches(storage: Storage, name: str, algoritme: str, waarde: str) -> bool:
    digest = HASHES[algoritme]()
    with storage.open(name, "rb") as f:
        for chunk in f.chunks():
            digest.update(chunk)
    expected = waarde.strip()
    return expected.lower() == digest.hexdigest() or expected == base64.b64encode(
        digest.digest()
    ).decode("ascii")


class Statistics:
    """
    Background rates: documents without a namesake can't be affected by concurrent
    unlocks, so their rates show what's normal for this installation.
    """

    def __init__(self):
        self.checked: Counter[bool] = Counter()
        self.found: Counter[tuple[bool, str]] = Counter()

    def count(self, has_namesake: bool, check: str | None):
        self.checked[has_namesake] += 1
        if check:
            self.found[has_namesake, check] += 1

    def lines(self) -> Iterator[str]:
        for check in ["wrong-size", "missing-file"]:
            rates = []
            for has_namesake, label in [(True, "with"), (False, "without")]:
                n, k = self.checked[has_namesake], self.found[has_namesake, check]
                low, high = wilson(k, n)
                rates.append(
                    f"{k}/{n} ({low:.2%}-{high:.2%}) {label} a namesake"
                    if n
                    else f"none checked {label} a namesake"
                )
            yield f"  {check}: " + ", ".join(rates)


def check_files(
    storage: Storage,
    namesakes: dict[str, NamesakeGroup],
    quick: bool,
    verify_integrity: bool,
    statistics: Statistics,
) -> Iterator[Finding]:
    """
    Files that are missing, or whose size or hash doesn't match the metadata. Files
    whose content couldn't be verified are assessed with the timing model.
    """
    documents = (
        EnkelvoudigInformatieObject.objects.exclude(inhoud="")
        .order_by("inhoud")
        .values(
            "pk",
            "uuid",
            "versie",
            "canonical",
            "inhoud",
            "bestandsnaam",
            "bestandsomvang",
            "begin_registratie",
            "integriteit_algoritme",
            "integriteit_waarde",
        )
    )
    # versions of a document share a file, only look it up once
    sizes: dict[str, int | None] = {}
    for document in documents.iterator():
        key = merge_key(document["bestandsnaam"])
        group = namesakes.get(key) if key is not None else None
        if quick and group is None:
            continue

        name = normalize(document["inhoud"])
        uuid, versie = str(document["uuid"]), document["versie"]
        bestandsomvang = document["bestandsomvang"]
        evidence = {"file": name, "bestandsomvang": bestandsomvang}

        if name not in sizes:
            sizes.clear()
            sizes[name] = None
            try:
                sizes[name] = storage.size(name)
            except Exception as exc:
                try:
                    missing = not storage.exists(name)
                except Exception:
                    missing = False
                if missing:
                    statistics.count(group is not None, "missing-file")
                    yield Finding(
                        POSSIBLE, "missing-file", uuid, versie, name, evidence
                    )
                else:
                    yield Finding(
                        POSSIBLE, "not-checked", uuid, versie, f"{name}: {exc!r}"
                    )
                continue
        size = sizes[name]
        if size is None:
            continue
        evidence["size"] = size

        if bestandsomvang is not None and size != bestandsomvang:
            statistics.count(group is not None, "wrong-size")
            yield Finding(
                AFFECTED,
                "wrong-size",
                uuid,
                versie,
                f"{name}: {size} bytes, bestandsomvang is {bestandsomvang}",
                evidence,
            )
            continue
        statistics.count(group is not None, None)

        algoritme = document["integriteit_algoritme"]
        waarde = document["integriteit_waarde"]
        if not (algoritme and waarde):
            reason = "no integriteit"
        elif algoritme not in HASHES:
            reason = f"unsupported integriteit algoritme {algoritme}"
        elif not verify_integrity:
            reason = "integriteit not verified, use --verify-integrity"
        else:
            try:
                matches = hash_matches(storage, name, algoritme, waarde)
            except Exception as exc:
                yield Finding(POSSIBLE, "not-checked", uuid, versie, f"{name}: {exc!r}")
                continue
            if matches:
                continue
            yield Finding(
                AFFECTED,
                "wrong-hash",
                uuid,
                versie,
                f"{name}: {algoritme} doesn't match",
                evidence,
            )
            continue
        evidence["unverified"] = reason

        if group is not None:
            strength, nearest, overlap = group.assess(document["pk"])
            yield Finding(
                strength,
                "same-name",
                uuid,
                versie,
                f"{name}: {describe_overlap(strength, nearest, overlap)}; {reason}",
                evidence | overlap,
            )
        elif bestandsomvang is None:
            yield Finding(
                UNLIKELY,
                "size-unknown",
                uuid,
                versie,
                f"{name}: no bestandsomvang, {reason}",
                evidence,
            )


class Command(BaseCommand):
    help = (
        "Report documents whose content may have been overwritten or lost "
        "(open-zaak#2592). Prints one tab separated line per finding: strength, "
        "check, uuid, versie, detail; and a summary with background rates. "
        "'affected': almost certainly lost their content. "
        "'possible': can't be ruled out; inspect these. "
        "'unlikely': ruled out by the timing model or rare causes only. "
        "See the Open Zaak documentation, 'Detecting overwritten documents', for "
        "the reasoning and when it can fail."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify-integrity",
            action="store_true",
            help=(
                "Also read every file with an integriteit to verify its hash "
                f"({', '.join(HASHES)}). On Azure and S3 this downloads them."
            ),
        )
        parser.add_argument(
            "--quick",
            action="store_true",
            help=(
                "Only check the files of documents with the same name as another "
                "document. Misses wrong sizes and missing files of other documents."
            ),
        )
        parser.add_argument(
            "--min-throughput",
            type=float,
            default=256,
            metavar="KIB_PER_S",
            help=(
                "Slowest plausible speed of merging and storing a document during an "
                "unlock, in KiB/s (default: 256). Lower is more cautious."
            ),
        )
        parser.add_argument(
            "--margin",
            type=float,
            default=30,
            metavar="SECONDS",
            help=(
                "Extra time for request overhead and clock differences between "
                "servers (default: 30). Higher is more cautious."
            ),
        )
        parser.add_argument(
            "--format",
            choices=["tsv", "jsonl"],
            default="tsv",
            help="jsonl includes all evidence per finding (default: tsv).",
        )

    def handle(self, *args, **options):
        timing = Timing(
            min_throughput=options["min_throughput"] * 1024, margin=options["margin"]
        )
        statistics = Statistics()
        edited = find_edited_in_admin()
        namesakes = {
            key: NamesakeGroup(versions, edited, timing)
            for key, versions in find_namesakes().items()
        }
        findings = itertools.chain(
            find_shared_files(),
            find_failed_unlocks(),
            check_files(
                get_storage(),
                namesakes,
                options["quick"],
                options["verify_integrity"],
                statistics,
            ),
        )

        # written as they're found: a run can take hours, and may be interrupted
        counts = Counter()
        if options["format"] == "tsv":
            self.stdout.write("strength\tcheck\tuuid\tversie\tdetail")
        for finding in findings:
            counts[finding.strength, finding.check] += 1
            if options["format"] == "jsonl":
                line = json.dumps(
                    {
                        "strength": finding.strength,
                        "check": finding.check,
                        "uuid": finding.uuid,
                        "versie": finding.versie,
                        "detail": finding.detail,
                        "evidence": finding.evidence,
                    },
                    default=str,
                )
            else:
                line = (
                    f"{finding.strength}\t{finding.check}\t{finding.uuid}\t"
                    f"{finding.versie}\t{escape(finding.detail)}"
                )
            self.stdout.write(line)
            self.stdout.flush()

        self.write_summary(counts, statistics, timing, options["quick"])

    def write_summary(self, counts, statistics, timing, quick):
        meaning = {
            AFFECTED: "almost certainly lost their content",
            POSSIBLE: "can't be ruled out, inspect these",
            UNLIKELY: "ruled out by the timing model, or rare causes only",
        }
        for strength in STRENGTHS:
            checks = {c: n for (s, c), n in sorted(counts.items()) if s == strength}
            details = ", ".join(f"{n} {check}" for check, n in checks.items())
            total = sum(checks.values())
            self.stderr.write(
                f"{strength.capitalize()}: {total}"
                + (f" ({details})" if details else "")
                + f" - {meaning[strength]}"
            )
        self.stderr.write(
            f"Timing model: an unlock took at most bestandsomvang / "
            f"{timing.min_throughput / 1024:g} KiB/s + {timing.margin:g} s"
        )
        if quick:
            self.stderr.write("Only documents with a namesake were checked (--quick)")
        self.stderr.write("Background rates, with 95% intervals:")
        for line in statistics.lines():
            self.stderr.write(line)
