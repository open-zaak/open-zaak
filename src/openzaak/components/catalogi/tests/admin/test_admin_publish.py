# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.auth.models import Permission
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory, UserFactory
from openzaak.selectielijst.tests import (
    mock_oas_get,
    mock_resource_get,
    mock_resource_list,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.utils.tests import ClearCachesMixin

from ..factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


@requests_mock.Mocker()
class ZaaktypeAdminTests(ReferentieLijstServiceMixin, ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_publish_zaaktype(self, m):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertFalse(zaaktype.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

    def test_publish_besluittype(self, m):
        besluittype = BesluitTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["besluittype_form"]

        response = form.submit("_publish").follow()

        besluittype.refresh_from_db()
        self.assertFalse(besluittype.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

    def test_publish_informatieobjecttype(self, m):
        iot = InformatieObjectTypeFactory.create(
            concept=True, vertrouwelijkheidaanduiding="openbaar"
        )
        iot.zaaktypeinformatieobjecttype_set.all().delete()
        url = reverse("admin:catalogi_informatieobjecttype_change", args=(iot.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["informatieobjecttype_form"]

        response = form.submit("_publish").follow()

        iot.refresh_from_db()
        self.assertFalse(iot.concept)

        # Verify that the publish button is disabled
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNotNone(publish_button)

    def test_publish_zaaktype_related_to_concept_besluittype_fails(self, m):
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
        )
        BesluitTypeFactory.create(concept=True, zaaktypen=[zaaktype])
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

        # Check that the error is shown on the page
        error_message = response.html.find("li", {"class": "error"})
        self.assertIn("should be published", error_message.text)

        # Verify that the publish button is still visible and enabled.
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

    def test_publish_zaaktype_related_to_concept_informatieobjecttype_fails(self, m):
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=True, zaaktype=zaaktype
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        # Verify that the publish button is visible and enabled
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)

        form = response.forms["zaaktype_form"]

        response = form.submit("_publish").follow()

        zaaktype.refresh_from_db()
        self.assertTrue(zaaktype.concept)

        # Check that the error is shown on the page
        error_message = response.html.find("li", {"class": "error"})
        self.assertIn("should be published", error_message.text)

        # Verify that the publish button is still visible and enabled.
        publish_button = response.html.find("input", {"name": "_publish"})
        self.assertIsNotNone(publish_button)
        publish_button = response.html.find(
            "input", {"name": "_publish", "disabled": "disabled"}
        )
        self.assertIsNone(publish_button)


@tag("readonly-user")
class ReadOnlyUserTests(ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        user = UserFactory.create(is_staff=True)
        view_zaaktype = Permission.objects.get(codename="view_zaaktype")
        view_informatieobjecttype = Permission.objects.get(
            codename="view_informatieobjecttype"
        )
        view_besluittype = Permission.objects.get(codename="view_besluittype")
        user.user_permissions.add(
            view_zaaktype, view_informatieobjecttype, view_besluittype
        )

        cls.user = user

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_zaaktype_publish_not_possible(self):
        zaaktype = ZaakTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)

    def test_informatieobjecttype_publish_not_possible(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)

    def test_besluittype_publish_not_possible(self):
        besluittype = BesluitTypeFactory.create(concept=True)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        detail_page = self.app.get(url)

        html = detail_page.form.html
        self.assertNotIn(_("Publiceren"), html)

        # try to submit it anyway
        detail_page.form.submit("_publish", status=403)
