# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import tag
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from webtest import Upload

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)

from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


@disable_admin_mfa()
class EnkelvoudigInformatieObjectAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_add_informatieobject_page(self):
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        self.assertEqual(response.status_code, 200)

    def test_create_informatieobject_save(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.form

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"foo")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 302)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.canonical, canonical)
        self.assertEqual(eio.inhoud.read(), b"foo")

    @tag("gh-1306")
    def test_create_informatieobject_save_identificatie_all_characters_allowed(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.form

        form["identificatie"] = "some docüment"
        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"foo")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 302)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.identificatie, "some docüment")

    def test_create_without_iotype(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1441
        """
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.form

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"some content")

        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Je moet een informatieobjecttype opgeven", response.text)


@disable_admin_mfa()
class EnkelvoudigInformatieObjectCanonicalAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_eio_add_no_version(self):

        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)

        add_url = reverse("admin:documenten_enkelvoudiginformatieobjectcanonical_add")
        get_response = self.app.get(add_url)

        response = get_response.form.submit()
        self.assertEqual(response.status_code, 200)

        version_form = response.context["inline_admin_formsets"][0].forms[0]

        self.assertEqual(
            version_form.errors["bronorganisatie"], [_("This field is required.")]
        )
        self.assertEqual(
            version_form.errors["creatiedatum"], [_("This field is required.")]
        )
        self.assertEqual(version_form.errors["titel"], [_("This field is required.")])
        self.assertEqual(version_form.errors["auteur"], [_("This field is required.")])
        self.assertEqual(version_form.errors["taal"], [_("This field is required.")])
        self.assertEqual(
            version_form.errors["bestandsomvang"], [_("This field is required.")]
        )
        self.assertEqual(version_form.errors["inhoud"], [_("This field is required.")])
        self.assertEqual(
            version_form.errors["__all__"],
            [
                _("Constraint “%(name)s” is violated.")
                % {
                    "name": "documenten_enkelvoudiginformatieobject__informatieobjecttype_or"
                    "__informatieobjecttype_base_url_filled"
                }
            ],
        )
        # should still be zero
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)
