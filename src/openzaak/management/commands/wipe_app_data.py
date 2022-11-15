from collections import defaultdict

from django.core.management import BaseCommand
from django.db import transaction

from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.authorizations.models import Applicatie

from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from openzaak.components.zaken.models import (
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    RelevanteZaakRelatie,
    Resultaat,
    Rol,
    Status,
    Vestiging,
    Zaak,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakKenmerk,
)

TOP_LEVEL_RESOURCES = {
    "enkelvoudiginformatieobject": {
        "model": EnkelvoudigInformatieObject,
        "related_models": (
            (
                ObjectInformatieObject,
                lambda uuids: {
                    "informatieobject__enkelvoudiginformatieobject__uuid__in": uuids
                },
            ),
            (
                ZaakInformatieObject,
                lambda uuids: {
                    "_informatieobject__enkelvoudiginformatieobject__uuid__in": uuids
                },
            ),
            (
                Gebruiksrechten,
                lambda uuids: {
                    "informatieobjectenkelvoudiginformatieobject____uuid__in": uuids
                },
            ),
            (
                EnkelvoudigInformatieObjectCanonical,
                lambda uuids: {"enkelvoudiginformatieobject__isnull": True},
            ),
        ),
    },
    "zaak": {
        "model": Zaak,
        "related_models": (
            (ObjectInformatieObject, lambda uuids: {"_zaak__uuid__in": uuids}),
            (ZaakInformatieObject, lambda uuids: {"zaak__uuid__in": uuids}),
            (ZaakEigenschap, lambda uuids: {"zaak__uuid__in": uuids}),
            (ZaakKenmerk, lambda uuids: {"zaak__uuid__in": uuids}),
            (Status, lambda uuids: {"zaak__uuid__in": uuids}),
            (Resultaat, lambda uuids: {"zaak__uuid__in": uuids}),
            (OrganisatorischeEenheid, lambda uuids: {"rol__zaak__uuid__in": uuids}),
            (NatuurlijkPersoon, lambda uuids: {"rol__zaak__uuid__in": uuids}),
            (NietNatuurlijkPersoon, lambda uuids: {"rol__zaak__uuid__in": uuids}),
            (Vestiging, lambda uuids: {"rol__zaak__uuid__in": uuids}),
            (Medewerker, lambda uuids: {"rol__zaak__uuid__in": uuids}),
            (Rol, lambda uuids: {"zaak__uuid__in": uuids}),
            (RelevanteZaakRelatie, lambda uuids: {"zaak__uuid__in": uuids}),
        ),
    },
}


def wipe_data(resource: str, uuids):
    config = TOP_LEVEL_RESOURCES[resource]
    for related_model, build_filter in config["related_models"]:
        filter_expr = build_filter(uuids)
        qs = related_model.objects.filter(**filter_expr)
        qs._raw_delete("default")

    config["model"].objects.filter(uuid__in=uuids)._raw_delete("default")


class Command(BaseCommand):
    help = "Wipe the data created by the given application"

    def add_arguments(self, parser):
        parser.add_argument(
            "client_id", help="Client ID of the application to delete the data of."
        )

    @transaction.atomic()
    def handle(self, **options):
        app = Applicatie.objects.filter(
            client_ids__contains=[options["client_id"]]
        ).first()

        trails = AuditTrail.objects.filter(
            applicatie_id=str(app.uuid), resource__in=TOP_LEVEL_RESOURCES,
        )
        num = trails.count()
        self.stdout.write(f"Found {num} audit trail record(s) with data to delete.")
        if not num:
            return

        answer = input(
            "Are you sure you want to continue? This will permantently delete "
            "the data. [y/N]: "
        )
        if answer.lower().strip() != "y":
            self.stdout.write("Aborting...")
            return

        to_delete = defaultdict(list)
        for record in trails:
            uuid = record.resource_url.split("/")[-1]
            to_delete[record.resource].append(uuid)

        for resource, uuids in to_delete.items():
            wipe_data(resource, uuids)

        self.stdout.write("done.")
