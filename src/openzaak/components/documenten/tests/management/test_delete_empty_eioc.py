# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact

from datetime import date, timedelta

from django.core.management import call_command

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from openzaak.tests.utils import JWTAuthMixin, TestMigrations

from ...models import EnkelvoudigInformatieObjectCanonical
from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


class DeleteEmptyEIOCTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.client.raise_request_exception = False

    def test_basic(self):

        eioc = EnkelvoudigInformatieObjectCanonicalFactory()
        latest = eioc.latest_version
        zaak = ZaakFactory()
        zio = ZaakInformatieObjectFactory(informatieobject=eioc, zaak=zaak)

        besluit = BesluitFactory()
        bio = BesluitInformatieObjectFactory(informatieobject=eioc, besluit=besluit)

        latest.delete()

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 1)
        self.assertEqual(ZaakInformatieObject.objects.count(), 1)
        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        zio_url = reverse(zio)
        response = self.client.get(zio_url, **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        bio_url = reverse(bio)
        response = self.client.get(bio_url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = self.client.get(reverse(besluit))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse(zaak), **ZAAK_WRITE_KWARGS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        call_command("delete_empty_eioc")

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)
        self.assertEqual(ZaakInformatieObject.objects.count(), 0)
        self.assertEqual(BesluitInformatieObject.objects.count(), 0)


class DeleteEmptyEIOCMigrationTests(TestMigrations):
    """
    regression test for https://github.com/open-zaak/open-zaak/issues/1766
    """

    migrate_from = "0033_alter_enkelvoudiginformatieobject_identificatie"
    migrate_to = "0034_delete_empty_eioc"
    app = "documenten"

    def setUpBeforeMigration(self, apps):
        """
        set up zaken and documenten
        """
        Catalogus = apps.get_model("catalogi", "Catalogus")
        ZaakType = apps.get_model("catalogi", "ZaakType")
        EnkelvoudigInformatieObjectCanonical = apps.get_model(
            "documenten", "EnkelvoudigInformatieObjectCanonical"
        )
        ObjectInformatieObject = apps.get_model("documenten", "ObjectInformatieObject")
        # EnkelvoudigInformatieObject = self.old_state.apps.get_model("documenten", "EnkelvoudigInformatieObject")
        ZaakIdentificatie = apps.get_model("zaken", "ZaakIdentificatie")
        Zaak = apps.get_model("zaken", "Zaak")
        ZaakInformatieObject = apps.get_model("zaken", "ZaakInformatieObject")

        # use bulk create to avoid etag calculation trigger
        # catalogi
        catalogus = Catalogus(
            domein="AAAAA",
            naam="Some Catalogus",
            rsin="000000000",
        )
        Catalogus.objects.bulk_create([catalogus])
        zaaktype = ZaakType(
            catalogus=catalogus,
            zaaktype_omschrijving="zaaktype 1",
            vertrouwelijkheidaanduiding="openbaar",
            doel="some goal",
            aanleiding="test",
            indicatie_intern_of_extern="extern",
            handeling_initiator="test",
            onderwerp="test",
            handeling_behandelaar="test",
            doorlooptijd_behandeling=timedelta(days=10),
            opschorting_en_aanhouding_mogelijk=True,
            verlenging_mogelijk=True,
            publicatie_indicatie=True,
            versiedatum=date(2024, 1, 1),
            verantwoordelijke="063308836",
            referentieproces_naam="test",
            datum_begin_geldigheid=date(2024, 1, 1),
        )
        ZaakType.objects.bulk_create([zaaktype])

        # documenten
        canonical = EnkelvoudigInformatieObjectCanonical.objects.create()

        # zaken
        zaak_identificatie = ZaakIdentificatie.objects.create(
            bronorganisatie="517439943",
            identificatie="ZAAK1",
        )
        zaak = Zaak(
            identificatie_ptr=zaak_identificatie,
            _zaaktype=zaaktype,
            verantwoordelijke_organisatie="063308836",
            startdatum=date(2024, 1, 1),
            vertrouwelijkheidaanduiding="openbaar",
        )
        Zaak.objects.bulk_create([zaak])
        zaak.refresh_from_db()
        # relations
        zio = ZaakInformatieObject(
            zaak=zaak,
            _informatieobject=canonical,
            aard_relatie="hoort_bij",
        )
        ZaakInformatieObject.objects.bulk_create([zio])
        ObjectInformatieObject.objects.create(
            informatieobject=canonical,
            object_type="zaak",
            _zaak=zaak,
        )

    def test_empty_canonical_removed(self):
        ZaakInformatieObject = self.apps.get_model("zaken", "ZaakInformatieObject")
        EnkelvoudigInformatieObjectCanonical = self.apps.get_model(
            "documenten", "EnkelvoudigInformatieObjectCanonical"
        )
        ObjectInformatieObject = self.apps.get_model(
            "documenten", "ObjectInformatieObject"
        )

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)
        self.assertEqual(ZaakInformatieObject.objects.count(), 0)
        self.assertEqual(ObjectInformatieObject.objects.count(), 0)
        self.assertEqual(ZaakInformatieObject.objects.count(), 0)
