# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.core.management import BaseCommand
from django.db import transaction

from vng_api_common.constants import RolTypes

from openzaak.components.zaken.models import NietNatuurlijkPersoon, Vestiging


class Command(BaseCommand):
    help = "Migrate deprecated Vestiging rollen to NietNatuurlijkePersoon."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            f"Attempting to migrate {Vestiging.objects.count()} Vestigingen to NietNatuurlijkePersonen..."
        )

        migration_count = 0
        for vestiging in Vestiging.objects.iterator():

            if NietNatuurlijkPersoon.objects.filter(rol=vestiging.rol).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Vestiging: (id={vestiging.id}): {vestiging.handelsnaam[0]} could not be migrated, "
                        f"a NietNatuurlijkPersoon already exists on Rol: {vestiging.rol.uuid}"
                    )
                )
                continue

            handelsnamen = ", ".join(vestiging.handelsnaam)
            max_length = NietNatuurlijkPersoon._meta.get_field(
                "statutaire_naam"
            ).max_length

            if len(handelsnamen) > max_length:
                self.stdout.write(
                    self.style.WARNING(
                        f"Vestiging: (id={vestiging.id}): {vestiging.handelsnaam[0]} could not be migrated, "
                        f"as its handelsnaam is too long. {len(handelsnamen)}/{max_length}"
                    )
                )
                continue

            rol = vestiging.rol

            nnp = NietNatuurlijkPersoon.objects.create(
                statutaire_naam=handelsnamen,
                kvk_nummer=vestiging.kvk_nummer,
                vestigings_nummer=vestiging.vestigings_nummer,
                rol=rol,
                zaakobject=vestiging.zaakobject,
            )

            rol.betrokkene_type = RolTypes.niet_natuurlijk_persoon
            rol.save()

            if sub_verblijf_buitenland := getattr(
                vestiging, "sub_verblijf_buitenland", None
            ):
                sub_verblijf_buitenland.vestiging = None
                sub_verblijf_buitenland.nietnatuurlijkpersoon = nnp
                sub_verblijf_buitenland.save()

            if verblijfsadres := getattr(vestiging, "verblijfsadres", None):
                verblijfsadres.vestiging = None
                verblijfsadres.nietnatuurlijkpersoon = nnp
                verblijfsadres.save()

            vestiging.delete()

            migration_count += 1

        if migration_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated {migration_count} Vestigingen successfully!"
                )
            )
