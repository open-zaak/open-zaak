# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers

from datetime import date

from django.test import TestCase

from freezegun.api import freeze_time
from hypothesis import given, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from openzaak.components.zaken.models import ZaakIdentificatie
from openzaak.components.zaken.models.identification_classes import (
    CreationYearIdentification,
    StartDatumYearIdentification,
    UWVIdentification,
)


class UWVIdentificationTests(TestCase):
    def setUp(self):
        self.uwv = UWVIdentification("111222333")

    def test_current(self):
        with self.subTest("No identificatie"):
            self.assertEqual(self.uwv.current(), "A00000000")

        with self.subTest("existing identificatie"):
            ZaakIdentificatie.objects.create(identificatie="A00000006")
            self.assertEqual(self.uwv.current(), "A00000006")

        with self.subTest("other identificatie"):
            ZaakIdentificatie.objects.create(identificatie="ZAAK-2026-0000001")
            self.assertEqual(self.uwv.current(), "A00000006")

        with self.subTest("later identificatie"):
            ZaakIdentificatie.objects.create(identificatie="B00000001")
            self.assertEqual(self.uwv.current(), "B00000001")

    def test_next(self):
        self.assertEqual(next(self.uwv._sequence("A00000000")), "A00000006")
        self.assertEqual(next(self.uwv._sequence("A00000006")), "A00000023")
        self.assertEqual(next(self.uwv._sequence("A99999999")), "B00000001")
        self.assertEqual(next(self.uwv._sequence("Z99999988")), "Z99999990")
        self.assertEqual(next(self.uwv._sequence("Z99999999")), "AA00000001")
        self.assertEqual(next(self.uwv._sequence("AA9999999")), "AB00000003")
        self.assertEqual(next(self.uwv._sequence("AZ9999999")), "BA00000002")

        with self.assertRaises(ValueError):
            next(self.uwv._sequence("ZZ99999999"))

    def test_generate(self):
        with self.subTest("from 0"):
            self.uwv.generate()

            self.assertEqual(ZaakIdentificatie.objects.count(), 1)
            iden = ZaakIdentificatie.objects.get()

            self.assertEqual(iden.identificatie, "A00000006")
            self.assertEqual(iden.bronorganisatie, "111222333")

        with self.subTest("next"):
            self.uwv.generate()

            self.assertEqual(ZaakIdentificatie.objects.count(), 2)
            self.assertEqual(
                ZaakIdentificatie.objects.last().identificatie, "A00000023"
            )

        with self.subTest("AA"):
            ZaakIdentificatie.objects.create(
                identificatie="Z99999990", bronorganisatie="111222333"
            )
            self.uwv.generate()
            self.assertEqual(
                ZaakIdentificatie.objects.last().identificatie, "AA00000001"
            )

    def test_generate_bulk(self):
        self.uwv.generate_bulk(5)

        self.assertEqual(ZaakIdentificatie.objects.count(), 5)

        expected = ["A00000006", "A00000023", "A00000037", "A00000040", "A00000054"]

        for i, iden in enumerate(ZaakIdentificatie.objects.all()):
            self.assertEqual(iden.identificatie, expected[i])


# A, ..., Z, AA, AB, ..., AZ, BA, ... ZZ
_LETTER_SEQUENCE = [chr(n + 65) for n in range(26)] + [
    chr(fst + 65) + chr(snd + 65) for fst in range(26) for snd in range(26)
]
assert _LETTER_SEQUENCE[0] == "A"
assert _LETTER_SEQUENCE[_LETTER_SEQUENCE.index("AA") + 1] == "AB"
assert _LETTER_SEQUENCE[_LETTER_SEQUENCE.index("AZ") + 1] == "BA"


def _uwv_identifier() -> st.SearchStrategy[str]:
    # this composite is better at searching the space for edge cases than
    # st.from_regex(r"^[A-Z]{1,2}[0-9]{8}$", fullmatch=True))
    return st.tuples(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=2),
        st.integers(min_value=0, max_value=99_999_999).map(lambda n: f"{n:08d}"),
    ).map("".join)


def _is_valid_uwv_identifier(identificatie: str) -> bool:
    """
    Chars multiplied by their position.
    A = 0, Z = 25
    total % 11 should be 10
    """
    chars = identificatie.strip("0123456789")
    digits = identificatie[len(chars) :]

    check = 0
    i = 1
    for c in chars:
        check += (ord(c) - 65) * i
        i += 1

    for d in digits:
        check += int(d) * i
        i += 1

    return check % 11 == 10


class UWVRandomTests(HypothesisTestCase):
    @given(current=_uwv_identifier())
    def test_uwv_generator(self, current):
        next_id = next(UWVIdentification("111222333")._sequence(current))
        self.assertTrue(_is_valid_uwv_identifier(next_id))
        self.assertTrue(len(next_id) > len(current) or next_id > current)

        # assert there is no other prefix in between current and next
        current_prefix = current.strip("0123456789")
        next_prefix = next_id.strip("0123456789")
        current_pos = _LETTER_SEQUENCE.index(current_prefix)
        next_pos = _LETTER_SEQUENCE.index(next_prefix)
        self.assertTrue((next_prefix == current_prefix) or next_pos == current_pos + 1)


@freeze_time("2026-01-01")
class CreationYearIdentificationTests(TestCase):
    def setUp(self):
        self.cyi = CreationYearIdentification("111222333")

    def test_current(self):
        with self.subTest("No identificatie"):
            self.assertEqual(self.cyi.current(), "ZAAK-2026-0000000000")

        with self.subTest("existing identificatie"):
            ZaakIdentificatie.objects.create(identificatie="ZAAK-2026-0000000001")
            self.assertEqual(self.cyi.current(), "ZAAK-2026-0000000001")

        with self.subTest("other identificatie"):
            ZaakIdentificatie.objects.create(identificatie="A00000006")
            self.assertEqual(self.cyi.current(), "ZAAK-2026-0000000001")

        with self.subTest("later identificatie"):
            ZaakIdentificatie.objects.create(identificatie="ZAAK-2026-1000000001")
            self.assertEqual(self.cyi.current(), "ZAAK-2026-1000000001")

    def test_next(self):
        self.assertEqual(
            next(self.cyi._sequence("ZAAK-2026-0000000001")), "ZAAK-2026-0000000002"
        )
        self.assertEqual(
            next(self.cyi._sequence("ZAAK-2026-0000000551")), "ZAAK-2026-0000000552"
        )
        self.assertEqual(
            next(self.cyi._sequence("ZAAK-2026-9999999999")), "ZAAK-2026-10000000000"
        )  # seems to be allowed in old generate?

    def test_generate(self):
        with self.subTest("from 0"):
            self.cyi.generate()

            self.assertEqual(ZaakIdentificatie.objects.count(), 1)
            iden = ZaakIdentificatie.objects.get()

            self.assertEqual(iden.identificatie, "ZAAK-2026-0000000001")
            self.assertEqual(iden.bronorganisatie, "111222333")

        with self.subTest("next"):
            self.cyi.generate()

            self.assertEqual(ZaakIdentificatie.objects.count(), 2)
            self.assertEqual(
                ZaakIdentificatie.objects.last().identificatie, "ZAAK-2026-0000000002"
            )

    def test_generate_bulk(self):
        self.cyi.generate_bulk(5)

        self.assertEqual(ZaakIdentificatie.objects.count(), 5)

        expected = [
            "ZAAK-2026-0000000001",
            "ZAAK-2026-0000000002",
            "ZAAK-2026-0000000003",
            "ZAAK-2026-0000000004",
            "ZAAK-2026-0000000005",
        ]

        for i, iden in enumerate(ZaakIdentificatie.objects.all()):
            self.assertEqual(iden.identificatie, expected[i])


class StartDatumYearIdentificationTests(TestCase):
    def setUp(self):
        self.sdi = StartDatumYearIdentification("111222333", date(2025, 1, 1))

    def test_current(self):
        self.assertEqual(self.sdi.current(), "ZAAK-2025-0000000000")

    def test_next(self):
        self.assertEqual(
            next(self.sdi._sequence("ZAAK-2025-0000000001")), "ZAAK-2025-0000000002"
        )

    def test_generate(self):
        self.sdi.generate()

        self.assertEqual(ZaakIdentificatie.objects.count(), 1)
        iden = ZaakIdentificatie.objects.get()

        self.assertEqual(iden.identificatie, "ZAAK-2025-0000000001")
        self.assertEqual(iden.bronorganisatie, "111222333")
