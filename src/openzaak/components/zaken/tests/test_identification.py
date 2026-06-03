from datetime import date

from django.test import TestCase

from freezegun.api import freeze_time

from openzaak.components.zaken.api.identification import (
    CreationYearIdentification,
    StartDatumYearIdentification,
    UWVIdentification,
)
from openzaak.components.zaken.models import ZaakIdentificatie


class UWVIdentificationTests(TestCase):
    def setUp(self):
        self.uwv = UWVIdentification({"bronorganisatie": "111222333"})

    def test_current(self):
        with self.subTest("No identificatie"):
            self.assertEqual(self.uwv.current(), "A00000005")

        with self.subTest("existing identificatie"):
            ZaakIdentificatie.objects.create(identificatie="A00000006")
            self.assertEqual(self.uwv.current(), "A00000006")

        with self.subTest("other identificatie"):
            ZaakIdentificatie.objects.create(identificatie="ZAAK-2026-0000001")
            self.assertEqual(self.uwv.current(), "A00000006")

        with self.subTest("later identificatie"):
            ZaakIdentificatie.objects.create(identificatie="B00000001")
            self.assertEqual(self.uwv.current(), "B00000001")

    def test_split(self):
        self.assertEqual(self.uwv._split("A00000006"), ("A", "00000006"))
        self.assertEqual(self.uwv._split("ZZ00000006"), ("ZZ", "00000006"))

    def test_validate(self):
        self.assertTrue(self.uwv._validate("A00000006"))
        self.assertTrue(self.uwv._validate("A00000023"))

        self.assertTrue(self.uwv._validate("B00000001"))
        self.assertTrue(self.uwv._validate("Z99999990"))
        self.assertTrue(self.uwv._validate("ZZ99999985"))

        self.assertFalse(self.uwv._validate("A00000000"))
        self.assertFalse(self.uwv._validate("ZZ99999990"))

    def test_increase(self):
        self.assertEqual(self.uwv._increase("A00000005"), "A00000006")
        self.assertEqual(self.uwv._increase("A99999999"), "B00000000")
        self.assertEqual(self.uwv._increase("B99999999"), "C00000000")
        self.assertEqual(self.uwv._increase("Z99999999"), "AA00000000")
        self.assertEqual(self.uwv._increase("AA99999999"), "AB00000000")
        self.assertEqual(self.uwv._increase("ZZ99999998"), "ZZ99999999")

        with self.assertRaises(ValueError):
            self.uwv._increase("ZZ99999999")

    def test_next(self):
        self.assertEqual(self.uwv._next("A00000000"), "A00000006")
        self.assertEqual(self.uwv._next("A00000006"), "A00000023")
        self.assertEqual(self.uwv._next("A99999999"), "B00000001")
        self.assertEqual(self.uwv._next("Z99999999"), "AA00000001")
        self.assertEqual(self.uwv._next("Z99999988"), "Z99999990")

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


@freeze_time("2026-01-01")
class CreationYearIdentificationTests(TestCase):
    def setUp(self):
        self.cyi = CreationYearIdentification({"bronorganisatie": "111222333"})

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
        self.assertEqual(self.cyi._next("ZAAK-2026-0000000001"), "ZAAK-2026-0000000002")
        self.assertEqual(self.cyi._next("ZAAK-2026-0000000551"), "ZAAK-2026-0000000552")
        self.assertEqual(
            self.cyi._next("ZAAK-2026-9999999999"), "ZAAK-2026-10000000000"
        )  # TODO seems to be allowed in old generate?

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
        self.sdi = StartDatumYearIdentification(
            {"bronorganisatie": "111222333", "startdatum": date(2025, 1, 1)}
        )

    def test_current(self):
        self.assertEqual(self.sdi.current(), "ZAAK-2025-0000000000")

    def test_next(self):
        self.assertEqual(self.sdi._next("ZAAK-2025-0000000001"), "ZAAK-2025-0000000002")

    def test_generate(self):
        self.sdi.generate()

        self.assertEqual(ZaakIdentificatie.objects.count(), 1)
        iden = ZaakIdentificatie.objects.get()

        self.assertEqual(iden.identificatie, "ZAAK-2025-0000000001")
        self.assertEqual(iden.bronorganisatie, "111222333")
