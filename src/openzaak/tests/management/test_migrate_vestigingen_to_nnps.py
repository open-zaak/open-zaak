# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from openzaak.components.zaken.models import (
    Adres,
    NietNatuurlijkPersoon,
    SubVerblijfBuitenland,
    Vestiging,
)
from openzaak.components.zaken.tests.factories import RolFactory, ZaakObjectFactory


class TestMigrateVestigingenToNnps(TestCase):

    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "migrate_vestigingen_to_nnps",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_migration(self):
        rol = RolFactory.create()
        zaak_object = ZaakObjectFactory.create()
        vestiging = Vestiging.objects.create(
            vestigings_nummer="12345",
            handelsnaam=["Maykin", "Maykin Media"],
            kvk_nummer="12345678",
            zaakobject=zaak_object,
            rol=rol,
        )

        sub_verblijf_buitenland = SubVerblijfBuitenland.objects.create(
            vestiging=vestiging, lnd_landcode="NL", lnd_landnaam="Nederland"
        )

        verblijfsadres = Adres.objects.create(
            vestiging=vestiging,
            wpl_woonplaats_naam="Amsterdam",
            gor_openbare_ruimte_naam="test",
            huisnummer=143,
        )

        result = self.call_command()

        self.assertIn("Migrated 1 Vestigingen successfully!", result)

        self.assertEqual(Vestiging.objects.count(), 0)
        self.assertEqual(NietNatuurlijkPersoon.objects.count(), 1)

        nnp = NietNatuurlijkPersoon.objects.get()
        self.assertEqual(nnp.vestigings_nummer, "12345")
        self.assertEqual(nnp.statutaire_naam, "Maykin, Maykin Media")
        self.assertEqual(nnp.kvk_nummer, "12345678")
        self.assertEqual(nnp.zaakobject, zaak_object)
        self.assertEqual(nnp.rol, rol)
        self.assertEqual(nnp.sub_verblijf_buitenland, sub_verblijf_buitenland)
        self.assertEqual(nnp.verblijfsadres, verblijfsadres)

    def test_vestiging_cannot_be_migrated_when_rol_already_has_nnp(self):

        rol = RolFactory.create()
        vestiging = Vestiging.objects.create(rol=rol)
        NietNatuurlijkPersoon.objects.create(rol=rol)

        result = self.call_command()

        self.assertIn(
            f"Vestiging: {', '.join(vestiging.handelsnaam)} could not be migrated, "
            f"a NietNatuurlijkPersoon already exists on Rol: {rol.uuid}",
            result,
        )

        self.assertEqual(Vestiging.objects.count(), 1)
        self.assertEqual(NietNatuurlijkPersoon.objects.count(), 1)
