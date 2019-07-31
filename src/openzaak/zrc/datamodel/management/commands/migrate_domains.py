from django.apps import apps
from django.core.management import BaseCommand

ZRC = ("https://ref.tst.vng.cloud/zrc/", "https://zaken-api.vng.cloud/")
DRC = ("https://ref.tst.vng.cloud/drc/", "https://documenten-api.vng.cloud/")
ZTC = ("https://ref.tst.vng.cloud/ztc/", "https://catalogi-api.vng.cloud/")
BRC = ("https://ref.tst.vng.cloud/brc/", "https://besluiten-api.vng.cloud/")
NRC = ("https://ref.tst.vng.cloud/nrc/", "https://notificaties-api.vng.cloud/")
AC = ("https://ref.tst.vng.cloud/ac/", "https://autorisaties-api.vng.cloud/")

VRL = ("https://ref.tst.vng.cloud/referentielijsten/", "https://referentielijsten-api.vng.cloud/")


def _base_mapping(variable: tuple) -> tuple:
    return (
        variable + ZRC,
        variable + DRC,
        variable + ZTC,
        variable + BRC,
        variable + NRC,
        variable + AC,
    )


BASE_MAPPING = (
    _base_mapping(("vng_api_common.APICredential", "api_root")) +
    _base_mapping(("authorizations.AuthorizationsConfig", "api_root")) +
    _base_mapping(("notifications.NotificationsConfig", "api_root"))
)

MAPPING = BASE_MAPPING + (
    ("datamodel.Zaak", "zaaktype", *ZTC),
    ("datamodel.Zaak", "communicatiekanaal", *VRL),
    ("datamodel.Zaak", "selectielijstklasse", *VRL),
    ("datamodel.RelevanteZaakRelatie", "url", *ZRC),
    ("datamodel.Status", "statustype", *ZTC),
    ("datamodel.Resultaat", "resultaattype", *ZTC),
    ("datamodel.ZaakEigenschap", "eigenschap", *ZTC),
    ("datamodel.ZaakInformatieObject", "informatieobject", *DRC),
    ("datamodel.ZaakBesluit", "besluit", *BRC),
)


class Command(BaseCommand):
    help = "Update data references from old to new domains"

    def handle(self, **options):
        for model, field, old, new in MAPPING:
            self.stdout.write(f"Migrating {model}.{field}")
            model = apps.get_model(model)

            objects = model.objects.filter(**{f"{field}__startswith": old})
            self.stdout.write(f"  Updating {objects.count()} objects...\n\n")
            for obj in objects:
                setattr(
                    obj,
                    field,
                    getattr(obj, field).replace(old, new, 1)
                )
                obj.save()
