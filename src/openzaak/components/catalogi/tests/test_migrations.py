# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from datetime import date

from django.db import connection

from openzaak.tests.utils import TestMigrations


def _create_zaaktype_and_iotype(apps):
    Catalogus = apps.get_model("catalogi", "Catalogus")
    InformatieObjectType = apps.get_model("catalogi", "InformatieObjectType")
    ZaakType = apps.get_model("catalogi", "ZaakType")

    catalogus = Catalogus.objects.create(
        _etag="",
        domein="TEST",
        rsin="000000000",
        contactpersoon_beheer_naam="Test",
    )
    iotype = InformatieObjectType.objects.create(
        _etag="",
        catalogus=catalogus,
        omschrijving="iotype",
        informatieobjectcategorie="test",
        vertrouwelijkheidaanduiding="openbaar",
        datum_begin_geldigheid=date(2020, 1, 1),
    )
    zaaktype = ZaakType.objects.create(
        _etag="",
        catalogus=catalogus,
        zaaktype_omschrijving="zaaktype",
        datum_begin_geldigheid=date(2020, 1, 1),
        vertrouwelijkheidaanduiding="openbaar",
        doel="doel",
        aanleiding="aanleiding",
        indicatie_intern_of_extern="intern",
        handeling_initiator="indienen",
        onderwerp="onderwerp",
        handeling_behandelaar="behandelen",
        doorlooptijd_behandeling="P30D",
        opschorting_en_aanhouding_mogelijk=False,
        verlenging_mogelijk=False,
        publicatie_indicatie=False,
        versiedatum=date(2020, 1, 1),
        verantwoordelijke="000000000",
        referentieproces_naam="proces",
    )
    return zaaktype, iotype


def _columns(table: str) -> set[str]:
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(cursor, table)
        }


class ZaakTypeInformatieObjectTypeLooseFkForwardTests(TestMigrations):
    """
    The existing informatieobjecttype foreign key is kept as the local part of the
    loose-fk field.
    """

    app = "catalogi"
    migrate_from = "0027_alter_resultaattype_brondatum_archiefprocedure_objecttype"
    migrate_to = "0028_informatieobjecttype_loose_fk"

    def setUpBeforeMigration(self, apps):
        ZaakTypeInformatieObjectType = apps.get_model(
            "catalogi", "ZaakTypeInformatieObjectType"
        )
        zaaktype, self.iotype = _create_zaaktype_and_iotype(apps)

        self.ztiot = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=self.iotype,
            volgnummer=1,
            richting="inkomend",
        )
        connection.check_constraints()

    def test_existing_relation_is_kept(self):
        ZaakTypeInformatieObjectType = self.apps.get_model(
            "catalogi", "ZaakTypeInformatieObjectType"
        )

        ztiot = ZaakTypeInformatieObjectType.objects.get(pk=self.ztiot.pk)

        self.assertEqual(ztiot._informatieobjecttype_id, self.iotype.pk)
        self.assertIsNone(ztiot._iotype_base_url)
        self.assertIsNone(ztiot._iotype_relative_url)

    def test_columns(self):
        columns = _columns("catalogi_zaaktypeinformatieobjecttype")

        self.assertIn("_informatieobjecttype_id", columns)
        self.assertIn("_iotype_base_url_id", columns)
        self.assertIn("_iotype_relative_url", columns)
        self.assertNotIn("informatieobjecttype_id", columns)


class ZaakTypeInformatieObjectTypeLooseFkBackwardTests(TestMigrations):
    app = "catalogi"
    migrate_from = "0028_informatieobjecttype_loose_fk"
    migrate_to = "0027_alter_resultaattype_brondatum_archiefprocedure_objecttype"

    def setUpBeforeMigration(self, apps):
        ZaakTypeInformatieObjectType = apps.get_model(
            "catalogi", "ZaakTypeInformatieObjectType"
        )
        zaaktype, self.iotype = _create_zaaktype_and_iotype(apps)

        self.ztiot = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            _informatieobjecttype=self.iotype,
            volgnummer=1,
            richting="inkomend",
        )
        connection.check_constraints()

    def test_relation_is_kept(self):
        ZaakTypeInformatieObjectType = self.apps.get_model(
            "catalogi", "ZaakTypeInformatieObjectType"
        )

        ztiot = ZaakTypeInformatieObjectType.objects.get(pk=self.ztiot.pk)

        self.assertEqual(ztiot.informatieobjecttype_id, self.iotype.pk)

    def test_columns(self):
        columns = _columns("catalogi_zaaktypeinformatieobjecttype")

        self.assertIn("informatieobjecttype_id", columns)
        self.assertNotIn("_informatieobjecttype_id", columns)
        self.assertNotIn("_iotype_base_url_id", columns)


def _create_besluittype(apps, catalogus):
    BesluitType = apps.get_model("catalogi", "BesluitType")
    return BesluitType.objects.create(
        _etag="",
        catalogus=catalogus,
        omschrijving="besluittype",
        publicatie_indicatie=False,
        datum_begin_geldigheid=date(2020, 1, 1),
    )


class BesluitTypeInformatieObjectTypenForwardTests(TestMigrations):
    app = "catalogi"
    migrate_from = "0028_informatieobjecttype_loose_fk"
    migrate_to = "0029_besluittype_informatieobjecttypen_through"

    def setUpBeforeMigration(self, apps):
        _, self.iotype = _create_zaaktype_and_iotype(apps)
        self.besluittype = _create_besluittype(apps, self.iotype.catalogus)
        self.other_besluittype = _create_besluittype(apps, self.iotype.catalogus)
        self.besluittype.informatieobjecttypen.add(self.iotype)
        connection.check_constraints()

    def test_relation_is_kept(self):
        BesluitTypeInformatieObjectType = self.apps.get_model(
            "catalogi", "BesluitTypeInformatieObjectType"
        )

        relations = BesluitTypeInformatieObjectType.objects.all()

        self.assertEqual(relations.count(), 1)
        self.assertEqual(relations[0].besluittype_id, self.besluittype.pk)
        self.assertEqual(relations[0]._informatieobjecttype_id, self.iotype.pk)

    def test_m2m_table_removed(self):
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)

        self.assertNotIn("catalogi_besluittype_informatieobjecttypen", tables)

    def test_reverse_accessors(self):
        BesluitType = self.apps.get_model("catalogi", "BesluitType")

        besluittype = BesluitType.objects.get(pk=self.besluittype.pk)

        self.assertEqual(
            list(besluittype.informatieobjecttypen.values_list("pk", flat=True)),
            [self.iotype.pk],
        )
        self.assertFalse(
            BesluitType.objects.get(
                pk=self.other_besluittype.pk
            ).informatieobjecttypen.exists()
        )


class BesluitTypeInformatieObjectTypenBackwardTests(TestMigrations):
    app = "catalogi"
    migrate_from = "0029_besluittype_informatieobjecttypen_through"
    migrate_to = "0028_informatieobjecttype_loose_fk"

    def setUpBeforeMigration(self, apps):
        BesluitTypeInformatieObjectType = apps.get_model(
            "catalogi", "BesluitTypeInformatieObjectType"
        )
        _, self.iotype = _create_zaaktype_and_iotype(apps)
        self.besluittype = _create_besluittype(apps, self.iotype.catalogus)
        BesluitTypeInformatieObjectType.objects.create(
            besluittype=self.besluittype, _informatieobjecttype=self.iotype
        )
        connection.check_constraints()

    def test_relation_is_restored(self):
        BesluitType = self.apps.get_model("catalogi", "BesluitType")

        besluittype = BesluitType.objects.get(pk=self.besluittype.pk)

        self.assertEqual(
            list(besluittype.informatieobjecttypen.values_list("pk", flat=True)),
            [self.iotype.pk],
        )
