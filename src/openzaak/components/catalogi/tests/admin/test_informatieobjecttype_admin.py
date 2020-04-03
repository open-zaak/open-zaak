from django.urls import reverse
from django.utils.http import urlencode

from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory

from ...models import ZaakType
from ..factories import (
    CatalogusFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
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

    def test_create_ziot_zaaktype_popup_filter_no_catalogus(self):
        response = self.app.get(
            reverse("admin:catalogi_zaaktypeinformatieobjecttype_add")
        )

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktype"})
        self.assertEqual(
            popup_zaaktypen.attrs["href"],
            f'{reverse("admin:catalogi_zaaktype_changelist")}?{urlencode({"_to_field": "id"})}',
        )
        # Verify that the popup screen shows only one Zaaktype
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])

        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 4)

    def test_create_ziot_zaaktype_popup_filter_with_catalogus(self):
        query_params = urlencode(
            {"catalogus_id__exact": self.catalogus.pk, "catalogus": self.catalogus.pk,}
        )
        url = f'{reverse("admin:catalogi_zaaktypeinformatieobjecttype_add")}?{query_params}'
        response = self.app.get(url)

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktype"})
        zaaktype_changelist_url = reverse("admin:catalogi_zaaktype_changelist")
        query_params = urlencode(
            {"_to_field": "id", "catalogus__exact": self.catalogus.pk}
        )
        self.assertEqual(
            popup_zaaktypen.attrs["href"], f"{zaaktype_changelist_url}?{query_params}",
        )
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

    def test_change_ziot_zaaktype_popup_filter(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=self.zaaktype, informatieobjecttype__catalogus=self.catalogus
        )
        response = self.app.get(
            reverse(
                "admin:catalogi_zaaktypeinformatieobjecttype_change", args=(ziot.pk,)
            )
        )

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktype"})
        zaaktype_changelist_url = reverse("admin:catalogi_zaaktype_changelist")
        query_param = urlencode(
            {"_to_field": "id", "catalogus__exact": self.catalogus.pk}
        )
        self.assertEqual(
            popup_zaaktypen.attrs["href"], f"{zaaktype_changelist_url}?{query_param}",
        )
        popup_response = self.app.get(popup_zaaktypen.attrs["href"])
        rows = popup_response.html.findAll("tr")[1:]
        self.assertEqual(len(rows), 1)

    def test_read_published_ziot_zaaktype_popup_filter(self):
        """
        There should be no popup links visible here, because the resource
        is published (and thus read only)
        """
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        response = self.app.get(
            reverse(
                "admin:catalogi_zaaktypeinformatieobjecttype_change", args=(ziot.pk,)
            )
        )

        popup_zaaktypen = response.html.find("a", {"id": "lookup_id_zaaktype"})
        self.assertIsNone(popup_zaaktypen)
