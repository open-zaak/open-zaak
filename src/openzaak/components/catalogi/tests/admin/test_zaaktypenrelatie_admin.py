# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.tests import reverse as _reverse

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.models import ZaakTypenRelatie
from openzaak.tests.utils import ClearCachesMixin

from ...constants import AardRelatieChoices
from ..factories import ZaakTypeFactory, ZaakTypenRelatieFactory


@disable_admin_mfa()
@override_settings(IS_HTTPS=False, ALLOWED_HOSTS=["testserver", "testserver.com"])
class ZaakTypenRelatieAdminTests(ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_zaaktypenrelatie_create_with_gerelateerd_zaaktype_internal(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2)

        zaaktype_url = f"http://testserver{_reverse(zaaktype1)}"

        url = reverse("admin:catalogi_zaaktypenrelatie_add")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )

        inputs = related_zaaktype.find_all("input")

        self.assertEqual(len(inputs), 2)

        form = response.form

        form["gerelateerd_zaaktype_0"] = zaaktype1.pk
        form["aard_relatie"] = AardRelatieChoices.vervolg
        form["zaaktype"] = zaaktype2.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        self.assertEqual(ZaakTypenRelatie.objects.count(), 1)

        relatie = ZaakTypenRelatie.objects.get()

        self.assertEqual(relatie.gerelateerd_zaaktype, zaaktype_url)
        self.assertEqual(relatie.aard_relatie, AardRelatieChoices.vervolg)
        self.assertEqual(relatie.zaaktype, zaaktype2)

    def test_zaaktypenrelatie_create_with_gerelateerd_zaaktype_external(self):
        zaaktype = ZaakTypeFactory.create()
        external_zt_url = "https://example.com/catalogi/api/v1/zaaktypen/68209b74-b5fe-4a8e-855f-7a6a9ba7056b"

        url = reverse("admin:catalogi_zaaktypenrelatie_add")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        inputs = related_zaaktype.find_all("input")

        self.assertEqual(len(inputs), 2)

        form = response.form

        form["gerelateerd_zaaktype_1"] = external_zt_url
        form["aard_relatie"] = AardRelatieChoices.vervolg
        form["zaaktype"] = zaaktype.pk

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        self.assertEqual(ZaakTypenRelatie.objects.count(), 1)

        relatie = ZaakTypenRelatie.objects.get()

        self.assertEqual(relatie.gerelateerd_zaaktype, external_zt_url)
        self.assertEqual(relatie.aard_relatie, AardRelatieChoices.vervolg)
        self.assertEqual(relatie.zaaktype, zaaktype)

    def test_zaaktypenrelatie_create_with_gerelateerd_zaaktype_both_internal_and_external_error(
        self,
    ):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2)

        zaaktype_url = f"http://testserver{_reverse(zaaktype1)}"

        url = reverse("admin:catalogi_zaaktypenrelatie_add")

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )

        inputs = related_zaaktype.find_all("input")

        self.assertEqual(len(inputs), 2)

        form = response.form

        # Filling in both values
        form["gerelateerd_zaaktype_0"] = zaaktype1.pk
        form["gerelateerd_zaaktype_1"] = zaaktype_url
        form["aard_relatie"] = AardRelatieChoices.vervolg
        form["zaaktype"] = zaaktype2.pk

        response = form.submit()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(ZaakTypenRelatie.objects.count(), 0)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        self.assertIsNotNone(related_zaaktype.find("ul", {"class": "errorlist"}))

    def test_zaaktypenrelatie_detail_concept(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2)

        zaaktype_url = f"http://testserver{_reverse(zaaktype1)}"

        relatie = ZaakTypenRelatieFactory.create(
            gerelateerd_zaaktype=zaaktype_url, zaaktype=zaaktype2
        )

        url = reverse("admin:catalogi_zaaktypenrelatie_change", args=(relatie.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        inputs = related_zaaktype.find_all("input")
        self.assertEqual(len(inputs), 2)

        form = response.form
        self.assertEqual(form["gerelateerd_zaaktype_0"].value, str(zaaktype1.pk))

        lookup = response.html.find("a", {"id": "lookup_id_gerelateerd_zaaktype_0"})
        self.assertIsNotNone(lookup)

        related_zaaktype_admin_link = related_zaaktype.find_all("a")[1]
        self.assertEqual(
            related_zaaktype_admin_link.attrs["href"],
            reverse("admin:catalogi_zaaktype_change", args=(zaaktype1.pk,)),
        )
        self.assertEqual(related_zaaktype_admin_link.text, str(zaaktype1))

    def test_zaaktypenrelatie_detail_not_concept(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, concept=False)

        zaaktype_url = f"http://testserver{_reverse(zaaktype1)}"

        relatie = ZaakTypenRelatieFactory.create(
            gerelateerd_zaaktype=zaaktype_url, zaaktype=zaaktype2
        )

        url = reverse("admin:catalogi_zaaktypenrelatie_change", args=(relatie.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        related_zaaktype_url = related_zaaktype.find("a")

        self.assertEqual(related_zaaktype_url.attrs["href"], zaaktype_url)
        self.assertEqual(related_zaaktype_url.text, zaaktype_url)

    def test_zaaktypenrelatie_detail_external(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2)

        relatie = ZaakTypenRelatieFactory.create(
            gerelateerd_zaaktype="http://catalogi.com/zaaktypen/1", zaaktype=zaaktype2
        )

        url = reverse("admin:catalogi_zaaktypenrelatie_change", args=(relatie.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        inputs = related_zaaktype.find_all("input")
        self.assertEqual(len(inputs), 2)

        form = response.form
        self.assertEqual(form["gerelateerd_zaaktype_0"].value, "")
        self.assertEqual(
            form["gerelateerd_zaaktype_1"].value, "http://catalogi.com/zaaktypen/1"
        )

        lookup = response.html.find("a", {"id": "lookup_id_gerelateerd_zaaktype_0"})
        self.assertIsNotNone(lookup)

    def test_zaaktypenrelatie_detail_with_external_url_internal_uuid(self):
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2)

        # External URL with the same UUID as an internal zaaktype
        external_zaaktype_url = f"http://catalogi.com/zaaktypen/{zaaktype2.uuid}"

        relatie = ZaakTypenRelatieFactory.create(
            gerelateerd_zaaktype=external_zaaktype_url, zaaktype=zaaktype2
        )

        url = reverse("admin:catalogi_zaaktypenrelatie_change", args=(relatie.pk,))

        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        related_zaaktype = response.html.find(
            "div", {"class": "field-gerelateerd_zaaktype"}
        )
        inputs = related_zaaktype.find_all("input")
        self.assertEqual(len(inputs), 2)

        form = response.form
        self.assertEqual(form["gerelateerd_zaaktype_0"].value, "")
        self.assertEqual(form["gerelateerd_zaaktype_1"].value, external_zaaktype_url)

        lookup = response.html.find("a", {"id": "lookup_id_gerelateerd_zaaktype_0"})
        self.assertIsNotNone(lookup)
