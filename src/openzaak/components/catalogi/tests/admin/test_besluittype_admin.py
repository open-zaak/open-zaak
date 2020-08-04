# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse
from django.utils.http import urlencode

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import BesluitType, InformatieObjectType, ZaakType
from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)


class BesluitTypeAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

        self.catalogus = CatalogusFactory.create()

        # Delete automatically created ZaakTypen
        ZaakType.objects.all().delete()
        self.zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        ZaakTypeFactory.create_batch(3, catalogus=CatalogusFactory.create())

        # Delete automatically created IOTypen
        InformatieObjectType.objects.all().delete()
        self.iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus, zaaktypen=[]
        )
        InformatieObjectTypeFactory.create_batch(
            3, catalogus=CatalogusFactory.create(), zaaktypen=[]
        )

    def test_create_besluittype_m2m_relation_popup_filters_no_catalogus(self):
        response = self.app.get(reverse("admin:catalogi_besluittype_add"))

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktypen"})
        self.assertEqual(
            popup_zaaktypen.attrs["href"], reverse("admin:catalogi_zaaktype_changelist")
        )
        # Verify that the popup screen shows only one Zaaktype
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])

        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 4)

        popup_iotypen = response.html.find(
            "a", {"id": "lookup_id_informatieobjecttypen"}
        )
        self.assertEqual(
            popup_iotypen.attrs["href"],
            reverse("admin:catalogi_informatieobjecttype_changelist"),
        )
        # Verify that the popup screen shows only one IOtype
        popup_response = self.app.get(popup_iotypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 4)

    def test_create_besluittype_m2m_relation_popup_filters_with_catalogus(self):
        query_params = urlencode(
            {"catalogus_id__exact": self.catalogus.pk, "catalogus": self.catalogus.pk,}
        )
        url = f'{reverse("admin:catalogi_besluittype_add")}?{query_params}'
        response = self.app.get(url)

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktypen"})
        zaaktype_changelist_url = reverse("admin:catalogi_zaaktype_changelist")
        self.assertEqual(
            popup_zaaktypen.attrs["href"],
            f'{zaaktype_changelist_url}?{urlencode({"catalogus__exact": self.catalogus.pk})}',
        )
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

        popup_iotypen = response.html.find(
            "a", {"id": "lookup_id_informatieobjecttypen"}
        )
        iotype_changelist_url = reverse(
            "admin:catalogi_informatieobjecttype_changelist"
        )
        self.assertEqual(
            popup_iotypen.attrs["href"],
            f'{iotype_changelist_url}?{urlencode({"catalogus__exact": self.catalogus.pk})}',
        )
        popup_response = self.app.get(popup_iotypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

    def test_change_besluittype_m2m_relation_popup_filters(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype.zaaktypen.all().delete()
        response = self.app.get(
            reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))
        )

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktypen"})
        zaaktype_changelist_url = reverse("admin:catalogi_zaaktype_changelist")
        self.assertEqual(
            popup_zaaktypen.attrs["href"],
            f'{zaaktype_changelist_url}?{urlencode({"catalogus__exact": self.catalogus.pk})}',
        )
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

        popup_iotypen = response.html.find(
            "a", {"id": "lookup_id_informatieobjecttypen"}
        )
        iotype_changelist_url = reverse(
            "admin:catalogi_informatieobjecttype_changelist"
        )
        self.assertEqual(
            popup_iotypen.attrs["href"],
            f'{iotype_changelist_url}?{urlencode({"catalogus__exact": self.catalogus.pk})}',
        )
        popup_response = self.app.get(popup_iotypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

    def test_read_published_besluittype_m2m_relation(self):
        """
        There should be no popup links visible here, because the resource
        is published (and thus read only)
        """
        besluittype = BesluitTypeFactory.create(concept=False)
        response = self.app.get(
            reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))
        )

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktypen"})
        self.assertIsNone(popup_zaaktypen)
        popup_iotypen = response.html.find(
            "a", {"id": "lookup_id_informatieobjecttypen"}
        )
        self.assertIsNone(popup_iotypen)

    def test_create_besluittype(self):
        query_params = urlencode(
            {"catalogus_id__exact": self.catalogus.pk, "catalogus": self.catalogus.pk,}
        )
        url = f'{reverse("admin:catalogi_besluittype_add")}?{query_params}'
        response = self.app.get(url)

        form = response.form
        form["datum_begin_geldigheid"] = "2019-01-01"
        form["zaaktypen"] = [self.zaaktype.id]

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location, reverse("admin:catalogi_besluittype_changelist")
        )

        self.assertEqual(BesluitType.objects.count(), 1)

    def test_change_besluittype(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype.zaaktypen.all().delete()
        response = self.app.get(
            reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))
        )

        form = response.form
        form["datum_begin_geldigheid"] = "2019-01-01"
        form["zaaktypen"] = [self.zaaktype.id]

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location, reverse("admin:catalogi_besluittype_changelist")
        )

        self.assertEqual(BesluitType.objects.count(), 1)
