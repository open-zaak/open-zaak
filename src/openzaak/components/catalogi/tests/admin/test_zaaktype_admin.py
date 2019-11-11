from django.test import TestCase
from django.urls import reverse

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import ZaakTypeFactory


class ZaaktypeAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        self.client.force_login(self.user)

    def test_zaaktype_detail(self):
        zaaktype = ZaakTypeFactory.create()
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
