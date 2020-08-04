# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase

from vng_api_common.constants import VertrouwelijkheidsAanduiding

from ...admin.forms import ZaakTypeForm
from ...constants import InternExtern
from ..factories import ZaakTypeFactory


class ZaaktypeValidationTests(TestCase):
    """
    Test the validation on Zaaktype
    """

    def test_same_id_different_dates(self):
        zaaktype = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            identificatie=1,
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
        )
        catalogus = zaaktype.catalogus

        form = ZaakTypeForm(
            data={
                "uuid": uuid.uuid4(),
                "catalogus": catalogus.id,
                "identificatie": 1,
                "zaaktype_omschrijving": "test",
                "datum_begin_geldigheid": "2019-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "doel": "some",
                "aanleiding": "test",
                "indicatie_intern_of_extern": InternExtern.extern,
                "handeling_initiator": "aanvragen",
                "onderwerp": "Klacht",
                "handeling_behandelaar": "behandelen",
                "doorlooptijd_behandeling_days": "10",
                "verantwoordelijke": "data",
                "versiedatum": "2019-01-01",
                "producten_of_diensten": ["http://example.com/producten_of_diensten/1"],
                "referentieproces_naam": "test",
                "trefwoorden": [],
                "verantwoordingsrelatie": [],
            }
        )

        valid = form.is_valid()

        self.assertTrue(valid)

    def test_same_id_overlapping_dates(self):
        zaaktype = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            identificatie=1,
            datum_begin_geldigheid="2018-01-01",
            datum_einde_geldigheid="2018-12-31",
        )
        catalogus = zaaktype.catalogus

        form = ZaakTypeForm(
            data={
                "uuid": uuid.uuid4(),
                "catalogus": catalogus.id,
                "identificatie": 1,
                "zaaktype_omschrijving": "test",
                "datum_begin_geldigheid": "2018-10-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "doel": "some",
                "aanleiding": "test",
                "indicatie_intern_of_extern": InternExtern.extern,
                "handeling_initiator": "aanvragen",
                "onderwerp": "Klacht",
                "handeling_behandelaar": "behandelen",
                "doorlooptijd_behandeling": "10 00:00",
                "verantwoordelijke": "data",
                "versiedatum": "2018-10-01",
                "producten_of_diensten": ["http://example.com/producten_of_diensten/1"],
                "referentieproces_naam": "test",
                "trefwoorden": [],
                "verantwoordingsrelatie": [],
            }
        )

        valid = form.is_valid()

        self.assertFalse(valid)

        error = form.errors.as_data()["__all__"][0]
        self.assertEqual(
            error.message,
            "Zaaktype versies (dezelfde omschrijving) mogen geen overlappende geldigheid hebben.",
        )

    def test_same_id_no_end_date(self):
        zaaktype = ZaakTypeFactory.create(
            zaaktype_omschrijving="test",
            identificatie=1,
            datum_begin_geldigheid="2018-01-01",
        )
        catalogus = zaaktype.catalogus

        form = ZaakTypeForm(
            data={
                "uuid": uuid.uuid4(),
                "catalogus": catalogus.id,
                "identificatie": 1,
                "zaaktype_omschrijving": "test",
                "datum_begin_geldigheid": "2019-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "doel": "some",
                "aanleiding": "test",
                "indicatie_intern_of_extern": InternExtern.extern,
                "handeling_initiator": "aanvragen",
                "onderwerp": "Klacht",
                "handeling_behandelaar": "behandelen",
                "doorlooptijd_behandeling": "10 00:00",
                "verantwoordelijke": "data",
                "versiedatum": "2019-01-01",
                "producten_of_diensten": ["http://example.com/producten_of_diensten/1"],
                "referentieproces_naam": "test",
                "trefwoorden": [],
                "verantwoordingsrelatie": [],
            }
        )

        valid = form.is_valid()

        self.assertFalse(valid)

        error = form.errors.as_data()["__all__"][0]
        self.assertEqual(
            error.message,
            "Zaaktype versies (dezelfde omschrijving) mogen geen overlappende geldigheid hebben.",
        )
