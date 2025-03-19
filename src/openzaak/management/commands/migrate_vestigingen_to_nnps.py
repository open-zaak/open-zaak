# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.core.management import BaseCommand
from django.db import transaction

from openzaak.components.zaken.models import NietNatuurlijkPersoon, Vestiging


class Command(BaseCommand):
    help = "Migrate deprecated Vestiging rollen to NietNatuurlijkePersoon."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            f"Attempting to migrate {Vestiging.objects.count()} Vestigingen..."
        )

        migration_count = 0
        for vestiging in Vestiging.objects.all():

            if NietNatuurlijkPersoon.objects.filter(rol=vestiging.rol):
                self.stdout.write(
                    self.style.WARNING(
                        f"Vestiging: {', '.join(vestiging.handelsnaam)} could not be migrated, "
                        f"a NietNatuurlijkPersoon already exists on Rol: {vestiging.rol.uuid}"
                    )
                )
                continue

            nnp = NietNatuurlijkPersoon.objects.create(
                statutaire_naam=", ".join(vestiging.handelsnaam),
                kvk_nummer=vestiging.kvk_nummer,
                vestigings_nummer=vestiging.vestigings_nummer,
                rol=vestiging.rol,
                zaakobject=vestiging.zaakobject,
            )

            if verblijf := vestiging.sub_verblijf_buitenland:
                verblijf.vestiging = None
                verblijf.nietnatuurlijkpersoon = nnp
                verblijf.save()

            # TODO o2o verblijfsadres?

            vestiging.delete()

            migration_count += 1

        if migration_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated {migration_count} Vestigingen successfully!"
                )
            )
