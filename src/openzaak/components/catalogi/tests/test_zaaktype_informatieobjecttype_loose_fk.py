# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase, override_settings

from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from ..api.filters import ZaakTypeInformatieObjectTypeFilter
from ..models import ZaakTypeInformatieObjectType
from .factories import (
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)

EXTERNAL_API_ROOT = "https://external.catalogi.nl/api/v1/"
EXTERNAL_IOTYPE = (
    f"{EXTERNAL_API_ROOT}informatieobjecttypen/2b2d2cb3-2a67-4b8e-a05f-cbbb7a0b3ff1"
)


class ZaakTypeInformatieObjectTypeLooseFkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = ServiceFactory.create(
            api_type=APITypes.ztc, api_root=EXTERNAL_API_ROOT
        )

    def test_local_informatieobjecttype(self):
        ztiot = ZaakTypeInformatieObjectTypeFactory.create()

        ztiot.refresh_from_db()

        self.assertIsNotNone(ztiot._informatieobjecttype)
        self.assertIsNone(ztiot._iotype_url)
        self.assertEqual(ztiot.informatieobjecttype, ztiot._informatieobjecttype)

    def test_external_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()

        ztiot = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=zaaktype,
            informatieobjecttype=EXTERNAL_IOTYPE,
            volgnummer=1,
            richting="inkomend",
        )

        ztiot.refresh_from_db()
        self.assertIsNone(ztiot._informatieobjecttype)
        self.assertEqual(ztiot._iotype_url, EXTERNAL_IOTYPE)
        self.assertEqual(ztiot._iotype_base_url, self.service)

    def test_informatieobjecttype_is_required(self):
        zaaktype = ZaakTypeFactory.create()

        with self.assertRaises(IntegrityError), transaction.atomic():
            ZaakTypeInformatieObjectType.objects.create(
                zaaktype=zaaktype, volgnummer=1, richting="inkomend"
            )

    def test_local_and_external_informatieobjecttype_is_not_allowed(self):
        zaaktype = ZaakTypeFactory.create()

        with self.assertRaises(IntegrityError), transaction.atomic():
            ZaakTypeInformatieObjectType.objects.create(
                zaaktype=zaaktype,
                _informatieobjecttype=InformatieObjectTypeFactory.create(),
                _iotype_url=EXTERNAL_IOTYPE,
                volgnummer=1,
                richting="inkomend",
            )

    def test_informatieobjecttype_lookup(self):
        local = ZaakTypeInformatieObjectTypeFactory.create()
        external = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=local.zaaktype,
            informatieobjecttype=EXTERNAL_IOTYPE,
            volgnummer=local.volgnummer + 1,
            richting="inkomend",
        )

        self.assertQuerySetEqual(
            ZaakTypeInformatieObjectType.objects.filter(
                informatieobjecttype=local.informatieobjecttype
            ),
            [local],
        )
        self.assertQuerySetEqual(
            ZaakTypeInformatieObjectType.objects.filter(
                informatieobjecttype=EXTERNAL_IOTYPE
            ),
            [external],
        )

    def test_zaaktypen_of_informatieobjecttype_only_local(self):
        local = ZaakTypeInformatieObjectTypeFactory.create()
        ZaakTypeInformatieObjectType.objects.create(
            zaaktype=ZaakTypeFactory.create(),
            informatieobjecttype=EXTERNAL_IOTYPE,
            volgnummer=1,
            richting="inkomend",
        )

        self.assertEqual(
            list(local.informatieobjecttype.zaaktypen.all()), [local.zaaktype]
        )


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class ZaakTypeInformatieObjectTypeFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=EXTERNAL_API_ROOT)

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.local_definitief = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=cls.zaaktype, informatieobjecttype__concept=False, volgnummer=1
        )
        cls.local_concept = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=cls.zaaktype, informatieobjecttype__concept=True, volgnummer=2
        )
        cls.external = ZaakTypeInformatieObjectType.objects.create(
            zaaktype=cls.zaaktype,
            informatieobjecttype=EXTERNAL_IOTYPE,
            volgnummer=3,
            richting="inkomend",
        )

    def _filter(self, data):
        request = RequestFactory().get("/", headers={"host": "openzaak.nl"})
        return ZaakTypeInformatieObjectTypeFilter(
            data=data,
            queryset=ZaakTypeInformatieObjectType.objects.all(),
            request=request,
        ).qs

    def test_filter_external_informatieobjecttype(self):
        result = self._filter({"informatieobjecttype": EXTERNAL_IOTYPE})

        self.assertQuerySetEqual(result, [self.external])

    def test_status_definitief_includes_external_informatieobjecttype(self):
        result = self._filter({"status": "definitief"})

        self.assertCountEqual(result, [self.local_definitief, self.external])

    def test_status_concept_excludes_external_informatieobjecttype(self):
        result = self._filter({"status": "concept"})

        self.assertCountEqual(result, [self.local_concept])

    def test_status_alles(self):
        result = self._filter({"status": "alles"})

        self.assertCountEqual(
            result, [self.local_definitief, self.local_concept, self.external]
        )
