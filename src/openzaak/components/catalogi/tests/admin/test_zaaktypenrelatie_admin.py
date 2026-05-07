# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.tests import reverse as _reverse

from openzaak.components.catalogi.models import ZaakTypenRelatie
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import ClearCachesMixin
from openzaak.tests.utils.admin import AdminTestMixin

from ...constants import AardRelatieChoices
from ..factories import ZaakTypeFactory, ZaakTypenRelatieFactory


@disable_admin_mfa()
@override_settings(IS_HTTPS=False, ALLOWED_HOSTS=["testserver", "testserver.com"])
class ZaakTypenRelatieAdminTests(ClearCachesMixin, AdminTestMixin, WebTest):
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

        form = response.forms["zaaktypenrelatie_form"]

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

        form = response.forms["zaaktypenrelatie_form"]

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

        form = response.forms["zaaktypenrelatie_form"]

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

        form = response.forms["zaaktypenrelatie_form"]
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

        form = response.forms["zaaktypenrelatie_form"]
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

        form = response.forms["zaaktypenrelatie_form"]
        self.assertEqual(form["gerelateerd_zaaktype_0"].value, "")
        self.assertEqual(form["gerelateerd_zaaktype_1"].value, external_zaaktype_url)

        lookup = response.html.find("a", {"id": "lookup_id_gerelateerd_zaaktype_0"})
        self.assertIsNotNone(lookup)


@tag("gh-1877")
@disable_admin_mfa()
class ZaakTypenRelatieDeleteAdminTests(AdminTestMixin, WebTest):
    def test_delete_published_zaaktypenrelatie_allowed_if_zaken_related(self):
        """
        Because zaaktypenrelaties are not relevant for runtime validation for zaken,
        deleting them should be possible
        """
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        relatie = ZaakTypenRelatieFactory.create(
            zaaktype=non_concept_zaaktype,
        )
        ZaakFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_zaaktypenrelatie_delete", args=(relatie.id,)
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # The relation are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_bulk_delete_published_zaaktypenrelaties_allowed_if_zaken_related(
        self,
    ):
        """
        Because zaaktypenrelaties are not relevant for runtime validation for zaken,
        deleting them should be possible
        """
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        relatie = ZaakTypenRelatieFactory.create(
            zaaktype=non_concept_zaaktype,
        )
        ZaakFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse("admin:catalogi_zaaktypenrelatie_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [relatie.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        # delete is allowed
        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_delete_published_zaaktypenrelatie_allowed_if_no_zaken_related(self):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        relatie = ZaakTypenRelatieFactory.create(zaaktype=non_concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_zaaktypenrelatie_delete",
            args=(relatie.id,),
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # The relation are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_bulk_delete_published_zaaktypenrelaties_allowed_if_no_zaken_related(
        self,
    ):
        non_concept_zaaktype = ZaakTypeFactory.create(concept=False)
        relatie = ZaakTypenRelatieFactory.create(
            zaaktype=non_concept_zaaktype,
        )
        concept_zaaktype = ZaakTypeFactory.create(concept=False)
        concept_relatie = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype,
        )

        admin_url = reverse("admin:catalogi_zaaktypenrelatie_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [relatie.id, concept_relatie.id]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_delete_concept_zaaktypenrelatie_allowed_if_zaken_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_relatie = ZaakTypenRelatieFactory.create(zaaktype=concept_zaaktype)

        ZaakFactory.create(zaaktype=concept_zaaktype)

        admin_url = reverse(
            "admin:catalogi_zaaktypenrelatie_delete",
            args=(concept_relatie.id,),
        )

        response = self.app.get(admin_url)

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # Relatie is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_bulk_delete_concept_zaaktypenrelaties_not_allowed_if_zaken_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_relatie1 = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype1,
        )
        ZaakFactory.create(zaaktype=concept_zaaktype1)

        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_relatie2 = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype2,
        )

        ZaakFactory.create(zaaktype=concept_zaaktype2)

        admin_url = reverse("admin:catalogi_zaaktypenrelatie_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_relatie1.id, concept_relatie2.id]

        response = form.submit()

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_delete_concept_zaaktypenrelatie_allowed_if_no_zaken_related(self):
        concept_zaaktype = ZaakTypeFactory.create(concept=True)
        concept_relatie = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype,
        )

        admin_url = reverse(
            "admin:catalogi_zaaktypenrelatie_delete", args=(concept_relatie.id,)
        )

        response = self.app.get(admin_url)

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # Both relaties are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())

    def test_bulk_delete_concept_zaaktypenrelaties_allowed_if_no_zaken_related(
        self,
    ):
        concept_zaaktype1 = ZaakTypeFactory.create(concept=True)
        concept_relatie1 = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype1,
        )
        concept_zaaktype2 = ZaakTypeFactory.create(concept=True)
        concept_relatie2 = ZaakTypenRelatieFactory.create(
            zaaktype=concept_zaaktype2,
        )

        admin_url = reverse("admin:catalogi_zaaktypenrelatie_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [concept_relatie1.id, concept_relatie2.id]

        response = form.submit()

        # no warning, because all relaties are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both relations are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ZaakTypenRelatie.objects.exists())
