# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import random
from itertools import groupby, islice

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone

import factory.fuzzy
from requests.exceptions import RequestException
from vng_api_common.client import Client, ClientError, to_internal_data
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from zgw_consumers.client import build_client

from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.catalogi.constants import ArchiefNominatieChoices
from openzaak.components.catalogi.models import (
    BesluitType,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.constants import ObjectInformatieObjectTypes
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    ObjectInformatieObject,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.models import (
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from openzaak.components.zaken.tests.factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from openzaak.selectielijst.api import get_resultaattype_omschrijvingen
from openzaak.selectielijst.models import ReferentieLijstConfig


def get_sl_resultaten() -> list[dict]:
    """
    get first 100 objects from Selectielijst.resultaten endpoint
    use only for test purposes
    """
    config = ReferentieLijstConfig.get_solo()
    client = build_client(config.service, client_factory=Client)
    assert client
    response_data = to_internal_data(client.get("resultaten"))
    assert isinstance(response_data, dict)
    return response_data["results"]


# django doesn't allow bulk crate for multitable inheritance, so
# here is some work-around how to do it including custom queryset and factory
class ZaakBulkFactory(factory.django.DjangoModelFactory):
    _zaaktype = factory.SubFactory(ZaakTypeFactory)
    vertrouwelijkheidaanduiding = factory.fuzzy.FuzzyChoice(
        choices=VertrouwelijkheidsAanduiding.values
    )
    registratiedatum = factory.Faker("date_this_month", before_today=True)
    startdatum = factory.Faker("date_this_month", before_today=True)
    bronorganisatie = factory.Faker("ssn", locale="nl_NL")
    verantwoordelijke_organisatie = factory.Faker("ssn", locale="nl_NL")
    identificatie = factory.Sequence(lambda n: "ZAAK_{}".format(n))
    archiefactiedatum = factory.Faker("future_date", end_date="+5y")
    archiefnominatie = factory.fuzzy.FuzzyChoice(choices=ArchiefNominatieChoices.values)

    class Meta:
        model = "zaken.Zaak"


class ZaakBulkQuerySet(models.QuerySet):
    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        assert batch_size is None or batch_size > 0
        if not objs:
            return objs

        self._for_write = True
        objs = list(objs)
        model = objs[0]._meta.model
        parent_model = model._meta.pk.related_model

        parent_objs = []
        for obj in objs:
            parent_values = {}
            for field in [f for f in parent_model._meta.fields if hasattr(obj, f.name)]:
                parent_values[field.name] = getattr(obj, field.name)
            parent_objs.append(parent_model(**parent_values))
            # setattr(obj, self.model._meta.pk.attname, obj.id)
        parent_objs = parent_model.objects.bulk_create(
            parent_objs, batch_size=batch_size
        )

        for obj, parent_obj in zip(objs, parent_objs):
            setattr(obj, model._meta.pk.attname, parent_obj.id)

        local_fields = [f for f in model._meta.local_fields if f.column]

        with transaction.atomic(using=self.db, savepoint=False):
            self._batched_insert(objs, local_fields, batch_size)

        return objs


class ZaakBulk(Zaak):
    objects_bulk = ZaakBulkQuerySet.as_manager()

    class Meta:
        proxy = True


# Besluit model doesn't allow bulk operations because of the signals
# Here we take care of it manually
# One more workaround, because without bulk_create it takes forever
class BesluitBulkFactory(BesluitFactory):
    identificatie = factory.Sequence(lambda n: "BESLUIT_{}".format(n))


class BesluitBulk(Besluit):
    objects_bulk = models.QuerySet.as_manager()

    class Meta:
        proxy = True


# ZaakInformatieObject, BesluitInformatieObject and ObjectInformatieObject
# models don't allow bulk operations because of the signals
# Here we take care of it manually
class ZaakInformatieObjectBulk(ZaakInformatieObject):
    objects = models.QuerySet.as_manager()

    class Meta:
        proxy = True


class BesluitInformatieObjectBulk(BesluitInformatieObject):
    objects = models.QuerySet.as_manager()

    class Meta:
        proxy = True


class ObjectInformatieObjectBulk(ObjectInformatieObject):
    objects = models.QuerySet.as_manager()

    class Meta:
        proxy = True


def split_every(n, iterable):
    """partition iterator"""
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))


class Command(BaseCommand):
    help = (
        "Generate data for performance testing. "
        "Can be used only on test and development environments."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--partition",
            type=int,
            default=10000,
            help="Number of objects to create at a time to prevent OOM killer",
        )
        parser.add_argument(
            "--zaken",
            dest="zaken_amount",
            type=int,
            default=1000000,
            help="Number of zaken, besluiten and documents to generate. Should be a multiple of 'zaaktypen'",
        )
        parser.add_argument(
            "--zaaktypen",
            dest="zaaktypen_amount",
            type=int,
            default=100,
            help="Number of zaaktypen, besluittypen and informatieobjecttypen to generate.",
        )

    def handle(self, *args, **options):
        self.partition = options["partition"]
        self.zaken_amount = options["zaken_amount"]
        self.zaaktypen_amount = options["zaaktypen_amount"]

        confirm = input(
            "Data generation should only be used for test purposes and should not be run in production.\n"
            "Are you sure you want to do this? Type 'yes' to continue, or 'no' to cancel: "
        )
        if confirm != "yes":
            raise CommandError("Data generation cancelled.")

        self.get_sl_data()
        self.generate_catalogi()
        self.generate_zaken()
        self.generate_besluiten()
        self.generate_documenten()
        self.generate_relations()

    def log_created(self, objs):
        self.stdout.write(
            f"{len(objs)} {objs[0]._meta.verbose_name_plural.lower()} created"
        )

    def bulk_create(self, model, objs):
        obj_name_plural = model._meta.verbose_name_plural
        for i, objs_batch in enumerate(split_every(self.partition, objs)):
            model.objects.bulk_create(objs_batch)
            self.stdout.write(f"Creating {obj_name_plural} for partition {i + 1}")
        self.stdout.write(f"Finished creating {obj_name_plural}")

    def get_sl_data(self):
        # request SL resultaten
        try:
            sl_resultaten = get_sl_resultaten()
        except (RequestException, ClientError):
            raise CommandError(
                "Selectielijst API is not available. Check its configuration"
            )

        self.sl_result_mapping = {
            res["procesType"]: res["url"] for res in sl_resultaten
        }

        # request SL resultaattype omschrijvingen
        self.sl_rt_omschrijvingen = [
            res["url"] for res in get_resultaattype_omschrijvingen()
        ]

    def generate_catalogi(self):
        #  catalog - 1
        catalog = CatalogusFactory.create(naam="performance test")
        self.log_created([catalog])

        # zaaktype - 100
        zaaktypen = ZaakTypeFactory.build_batch(
            self.zaaktypen_amount,
            selectielijst_procestype=random.choice(list(self.sl_result_mapping.keys())),
            catalogus=catalog,
            concept=False,
            with_identificatie=True,
        )
        zaaktypen = ZaakType.objects.bulk_create(zaaktypen)
        self.log_created(zaaktypen)

        # statustype - 300
        statustypen = []
        for zaaktype in zaaktypen:
            statustypen.extend(StatusTypeFactory.build_batch(3, zaaktype=zaaktype))
        statustypen = StatusType.objects.bulk_create(statustypen)
        self.log_created(statustypen)

        # resultaattype - 200
        resultaatypen = []
        for zaaktype in zaaktypen:
            resultaatypen.extend(
                ResultaatTypeFactory.build_batch(
                    2,
                    zaaktype=zaaktype,
                    selectielijstklasse=self.sl_result_mapping[
                        zaaktype.selectielijst_procestype
                    ],
                    resultaattypeomschrijving=random.choice(self.sl_rt_omschrijvingen),
                )
            )
        resultaatypen = ResultaatType.objects.bulk_create(resultaatypen)
        self.log_created(resultaatypen)

        # roltype - 100
        roltypen = []
        for zaaktype in zaaktypen:
            roltypen.append(RolTypeFactory.build(zaaktype=zaaktype))
        roltypen = RolType.objects.bulk_create(roltypen)
        self.log_created(roltypen)

        # eigenschap - 100
        # can't use bulk_create with eigenschappen
        eigenschappen = []
        for zaaktype in zaaktypen:
            eigenschappen.append(EigenschapFactory.create(zaaktype=zaaktype))
        self.log_created(eigenschappen)

        # informatieobjecttypen - 100
        iotypen = InformatieObjectTypeFactory.build_batch(
            self.zaaktypen_amount, catalogus=catalog, concept=False
        )
        iotypen = InformatieObjectType.objects.bulk_create(iotypen)
        self.log_created(iotypen)

        # zaaktype-informatieobjecttype - 100
        ztiotypen = []
        for zaaktype, iotype in zip(zaaktypen, iotypen):
            ztiotypen.append(
                ZaakTypeInformatieObjectTypeFactory.build(
                    zaaktype=zaaktype, informatieobjecttype=iotype
                )
            )
        ztiotypen = ZaakTypeInformatieObjectType.objects.bulk_create(ztiotypen)
        self.log_created(ztiotypen)

        # besluittype 100
        # can't use bulk_create because we need to specify m2m
        besluittypen = []
        for zaaktype, iotype in zip(zaaktypen, iotypen):
            besluittypen.append(
                BesluitTypeFactory.create(
                    catalogus=catalog,
                    concept=False,
                    informatieobjecttypen=[iotype],
                    zaaktypen=[zaaktype],
                )
            )
        self.log_created(besluittypen)

    def generate_zaken(self):
        # 1mln zaken
        zaken_per_zaaktype = self.zaken_amount // self.zaaktypen_amount
        zaaktypen = ZaakType.objects.order_by("id").all()
        for i, zaaktype in enumerate(zaaktypen):
            self.stdout.write(
                f"Creating {zaken_per_zaaktype} zaken for zaaktype {i+1} / {self.zaaktypen_amount}"
            )
            ZaakBulkFactory.reset_sequence(zaaktype.id * zaken_per_zaaktype)
            zaken = ZaakBulkFactory.build_batch(
                zaken_per_zaaktype,
                _zaaktype=zaaktype,
                zaakgeometrie=Point(random.uniform(1, 50), random.uniform(50, 100)),
                selectielijstklasse=self.sl_result_mapping[
                    zaaktype.selectielijst_procestype
                ],
            )

            ZaakBulk.objects_bulk.bulk_create(zaken)

        self.stdout.write("Adding more metadata to zaken...")

        zaken = Zaak.objects.order_by("id").all()

        def generate_zaak_resource(generate_from_zaak: callable):
            for zaak in zaken:
                obj_list = generate_from_zaak(zaak)
                yield from obj_list

        # 3 mln statussen
        statustypen = StatusType.objects.order_by("zaaktype", "id")
        zaaktype_statustypen = {}
        for zaaktype, group in groupby(statustypen, key=lambda x: x.zaaktype):
            zaaktype_statustypen[zaaktype.id] = [statustype for statustype in group]
        statussen_generator = generate_zaak_resource(
            lambda zaak: [
                StatusFactory.build(
                    zaak=zaak,
                    statustype=zaaktype_statustypen[zaak._zaaktype_id][i],
                    datum_status_gezet=timezone.now(),
                )
                for i in range(3)
            ]
        )
        self.bulk_create(Status, statussen_generator)

        # 1 mln resultaten
        resultaattypen = ResultaatType.objects.order_by("zaaktype", "id")
        zaaktype_resultaattypen = {}
        for zaaktype, group in groupby(resultaattypen, key=lambda x: x.zaaktype):
            zaaktype_resultaattypen[zaaktype.id] = [
                resultaattype for resultaattype in group
            ]

        resultaten_generator = generate_zaak_resource(
            lambda zaak: [
                ResultaatFactory.build(
                    zaak=zaak,
                    resultaattype=zaaktype_resultaattypen[zaak._zaaktype_id][
                        random.randint(0, 1)
                    ],
                )
            ]
        )
        self.bulk_create(Resultaat, resultaten_generator)

        # 1 mln rollen
        roltypen = RolType.objects.order_by("zaaktype", "id")
        zaaktype_roltypen = {}
        for zaaktype, group in groupby(roltypen, key=lambda x: x.zaaktype):
            zaaktype_roltypen[zaaktype.id] = [roltype for roltype in group]

        rollen_generator = generate_zaak_resource(
            lambda zaak: [
                RolFactory.build(
                    zaak=zaak, roltype=zaaktype_roltypen[zaak._zaaktype_id][0]
                )
            ]
        )
        self.bulk_create(Rol, rollen_generator)

        # 1 mln zaak-eigenschappen
        eigenschappen = Eigenschap.objects.order_by("zaaktype", "id")
        zaaktype_eigenschappen = {}
        for zaaktype, group in groupby(eigenschappen, key=lambda x: x.zaaktype):
            zaaktype_eigenschappen[zaaktype.id] = [eigenschap for eigenschap in group]

        zaakeigenschappen_generator = generate_zaak_resource(
            lambda zaak: [
                ZaakEigenschapFactory.build(
                    zaak=zaak, eigenschap=zaaktype_eigenschappen[zaak._zaaktype_id][0]
                )
            ]
        )
        self.bulk_create(ZaakEigenschap, zaakeigenschappen_generator)

        # 1 mln zaakobjecten
        zaakobject_generator = generate_zaak_resource(
            lambda zaak: [ZaakObjectFactory.build(zaak=zaak)]
        )
        self.bulk_create(ZaakObject, zaakobject_generator)

        self.stdout.write("Finished creating zaken")

    def generate_besluiten(self):
        besluiten_per_besluittype = self.zaken_amount // self.zaaktypen_amount
        besluittypen = BesluitType.objects.order_by("id").all()
        for i, besluittype in enumerate(besluittypen):
            self.stdout.write(
                f"Creating {besluiten_per_besluittype} besluiten for besluittype {i+1} / {len(besluittypen)}"
            )
            ZaakBulkFactory.reset_sequence(besluittype.id * besluiten_per_besluittype)
            besluiten = BesluitBulkFactory.build_batch(
                besluiten_per_besluittype, besluittype=besluittype
            )
            BesluitBulk.objects_bulk.bulk_create(besluiten)

        self.stdout.write("Finished creating besluiten")

    def generate_documenten(self):
        # documenten - 1 mln
        for i in range(self.zaken_amount // self.partition):
            self.stdout.write(
                f"Creating {self.partition} documenten for partition {i+1}"
            )
            eios_canonical = EnkelvoudigInformatieObjectCanonicalFactory.build_batch(
                self.partition, latest_version=None
            )
            EnkelvoudigInformatieObjectCanonical.objects.bulk_create(eios_canonical)

        self.stdout.write("Adding content and more metadata to documenten...")

        remainder = self.zaken_amount % self.partition
        if remainder:
            eios_canonical = EnkelvoudigInformatieObjectCanonicalFactory.build_batch(
                remainder, latest_version=None
            )
            EnkelvoudigInformatieObjectCanonical.objects.bulk_create(eios_canonical)

        def generate_enkelvoudiginformatieobjecten():
            eios_canonical = EnkelvoudigInformatieObjectCanonical.objects.order_by(
                "id"
            ).iterator()
            iotypen = InformatieObjectType.objects.order_by("id").all()
            for iotype in iotypen:
                for i in range(self.zaken_amount // self.zaaktypen_amount):
                    yield EnkelvoudigInformatieObjectFactory.build(
                        informatieobjecttype=iotype, canonical=next(eios_canonical)
                    )

        documenten_generator = generate_enkelvoudiginformatieobjecten()
        self.bulk_create(EnkelvoudigInformatieObject, documenten_generator)

        self.stdout.write("Finished creating documenten")

    def generate_relations(self):
        documenten = EnkelvoudigInformatieObjectCanonical.objects.order_by("id")

        def generate_document_relation(
            generate_from_relation_documenten: callable, model
        ):
            parent_objs = model.objects.order_by("id").all()
            for parent_obj, informatieobject in zip(parent_objs, documenten):
                objs = generate_from_relation_documenten(parent_obj, informatieobject)
                yield from objs

        # zio - 1 mln
        zio_generator = generate_document_relation(
            lambda zaak, informatieobject: [
                ZaakInformatieObjectFactory.build(
                    zaak=zaak, informatieobject=informatieobject
                )
            ],
            model=Zaak,
        )
        self.bulk_create(ZaakInformatieObjectBulk, zio_generator)

        # bio - 1 mln
        bio_generator = generate_document_relation(
            lambda besluit, informatieobject: [
                BesluitInformatieObjectFactory.build(
                    besluit=besluit, informatieobject=informatieobject
                )
            ],
            model=Besluit,
        )
        self.bulk_create(BesluitInformatieObjectBulk, bio_generator)

        # oio - 2 mln
        oio_zaak_generator = generate_document_relation(
            lambda zaak, informatieobject: [
                ObjectInformatieObject(
                    zaak=zaak,
                    informatieobject=informatieobject,
                    object_type=ObjectInformatieObjectTypes.zaak,
                )
            ],
            model=Zaak,
        )
        oio_besluit_generator = generate_document_relation(
            lambda besluit, informatieobject: [
                ObjectInformatieObject(
                    besluit=besluit,
                    informatieobject=informatieobject,
                    object_type=ObjectInformatieObjectTypes.besluit,
                )
            ],
            model=Besluit,
        )
        self.bulk_create(ObjectInformatieObjectBulk, oio_zaak_generator)
        self.bulk_create(ObjectInformatieObjectBulk, oio_besluit_generator)
