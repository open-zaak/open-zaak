# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import tag
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from openzaak.accounts.tests.factories import SuperUserFactory

from ..factories import ApplicatieFactory


@disable_admin_mfa()
class ApplicationsTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_create_applicatie_inline_credentials(self):
        url = reverse("admin:authorizations_applicatie_add")

        response = self.app.get(url)

        form = response.forms["applicatie_form"]
        form["label"] = "foo"

        self.assertFalse(form["alleen_is_gereed_voor_publicatie"].checked)
        form["alleen_is_gereed_voor_publicatie"].checked = True
        form["credentials-0-identifier"] = "foo"
        form["credentials-0-secret"] = "bar"

        form.submit().follow()

        self.assertEqual(JWTSecret.objects.count(), 1)
        self.assertEqual(Applicatie.objects.count(), 1)

        applicatie = Applicatie.objects.get()
        credential = JWTSecret.objects.get()

        self.assertEqual(applicatie.client_ids, ["foo"])
        self.assertTrue(applicatie.alleen_is_gereed_voor_publicatie)
        self.assertEqual(credential.identifier, "foo")
        self.assertEqual(credential.secret, "bar")

    @tag("gh-2452")
    def test_change_alleen_is_gereed_voor_publicatie(self):
        application = ApplicatieFactory.create(
            client_ids=[], alleen_is_gereed_voor_publicatie=False
        )
        url = reverse("admin:authorizations_applicatie_change", args=(application.pk,))

        for ready_for_publication in (True, False):
            with self.subTest(ready_for_publication=ready_for_publication):
                form = self.app.get(url).forms["applicatie_form"]
                self.assertEqual(
                    form["alleen_is_gereed_voor_publicatie"].checked,
                    application.alleen_is_gereed_voor_publicatie,
                )
                form[
                    "alleen_is_gereed_voor_publicatie"
                ].checked = ready_for_publication

                form.submit().follow()

                application.refresh_from_db()
                self.assertEqual(
                    application.alleen_is_gereed_voor_publicatie,
                    ready_for_publication,
                )

    @tag("gh-2452")
    def test_filter_by_alleen_is_gereed_voor_publicatie(self):
        ready_for_publication_only = ApplicatieFactory.create(
            alleen_is_gereed_voor_publicatie=True
        )
        all_documents = ApplicatieFactory.create(alleen_is_gereed_voor_publicatie=False)
        response = self.app.get(reverse("admin:authorizations_applicatie_changelist"))

        self.assertCountEqual(
            response.context["cl"].result_list,
            [ready_for_publication_only, all_documents],
        )
        self.assertIsNotNone(
            response.html.select_one("th.column-alleen_is_gereed_voor_publicatie")
        )
        for value, application in ((1, ready_for_publication_only), (0, all_documents)):
            with self.subTest(value=value):
                filtered = response.click(
                    href=rf"\?alleen_is_gereed_voor_publicatie__exact={value}$"
                )
                self.assertQuerySetEqual(
                    filtered.context["cl"].result_list, [application]
                )

    def test_delete_applicatie_cascade_inline_credentials(self):
        JWTSecret.objects.create(identifier="testid", secret="bla")
        applicatie = ApplicatieFactory.create(client_ids=["testid"])

        url = reverse("admin:authorizations_applicatie_delete", args=(applicatie.pk,))
        response = self.app.get(url)
        form = response.forms[1]
        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Applicatie.objects.count(), 0)
        self.assertEqual(JWTSecret.objects.count(), 0)

    def test_show_related_jwt_secrets(self):
        application = Applicatie.objects.create(label="test", client_ids=["foo"])
        JWTSecret.objects.create(identifier="foo", secret="bar")
        url = reverse("admin:authorizations_applicatie_change", args=(application.pk,))

        form = self.app.get(url).forms["applicatie_form"]

        self.assertEqual(form["credentials-0-identifier"].value, "foo")
        self.assertEqual(form["credentials-0-secret"].value, "bar")

        # nothing changes, check that our data doesn't get screwed on save
        form.submit().follow()

        application.refresh_from_db()
        self.assertEqual(application.client_ids, ["foo"])
        self.assertEqual(JWTSecret.objects.count(), 1)
        credential = JWTSecret.objects.get()
        self.assertEqual(credential.identifier, "foo")
        self.assertEqual(credential.secret, "bar")

    def test_delete_jwt_secret(self):
        application = Applicatie.objects.create(label="test", client_ids=["foo"])
        JWTSecret.objects.create(identifier="foo", secret="bar")
        url = reverse("admin:authorizations_applicatie_change", args=(application.pk,))

        form = self.app.get(url).forms["applicatie_form"]

        form["credentials-0-DELETE"].checked = True

        form.submit().follow()

        application.refresh_from_db()
        self.assertFalse(JWTSecret.objects.exists())
        self.assertEqual(application.client_ids, [])

    def test_change_jwt_secret(self):
        application = Applicatie.objects.create(label="test", client_ids=["foo"])
        JWTSecret.objects.create(identifier="foo", secret="bar")
        url = reverse("admin:authorizations_applicatie_change", args=(application.pk,))

        form = self.app.get(url).forms["applicatie_form"]

        form["credentials-0-identifier"] = "baz"
        form["credentials-0-secret"] = "quux"

        # nothing changes, check that our data doesn't get screwed on save
        form.submit().follow()

        application.refresh_from_db()
        self.assertEqual(application.client_ids, ["baz"])
        self.assertEqual(JWTSecret.objects.count(), 1)
        credential = JWTSecret.objects.get()
        self.assertEqual(credential.identifier, "baz")
        self.assertEqual(credential.secret, "quux")

    def test_create_applicatie_inline_credentials_without_secret(self):
        url = reverse("admin:authorizations_applicatie_add")

        response = self.app.get(url)

        form = response.forms["applicatie_form"]
        form["label"] = "foo"

        form["credentials-0-identifier"] = "foo"

        form.submit().follow()

        self.assertEqual(JWTSecret.objects.count(), 1)
        self.assertEqual(Applicatie.objects.count(), 1)

        applicatie = Applicatie.objects.get()
        credential = JWTSecret.objects.get()

        self.assertEqual(applicatie.client_ids, ["foo"])
        self.assertEqual(credential.identifier, "foo")
        self.assertEqual(credential.secret, "")

    def test_delete_selected_jwt_secret(self):
        """
        check that jwtsecrets are deleted when delete_selected admin action is used
        regression test for https://github.com/open-zaak/open-zaak/issues/1741
        """
        app1 = Applicatie.objects.create(label="test1", client_ids=["foo1"])
        app2 = Applicatie.objects.create(label="test2", client_ids=["foo2", "foo3"])
        JWTSecret.objects.create(identifier="foo1", secret="bar1")
        JWTSecret.objects.create(identifier="foo2", secret="bar2")
        JWTSecret.objects.create(identifier="foo3", secret="bar3")
        jwt_no_delete = JWTSecret.objects.create(
            identifier="no-delete", secret="no-delete"
        )
        url = reverse("admin:authorizations_applicatie_changelist")

        form = self.app.get(url).forms["changelist-form"]

        form["action"] = "delete_selected"
        form["_selected_action"] = [app1.id, app2.id]

        response = form.submit()

        # confirmation page
        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JWTSecret.objects.count(), 1)
        self.assertEqual(JWTSecret.objects.get(), jwt_no_delete)
