from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from openzaak.accounts.tests.factories import SuperUserFactory


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

        form = response.form
        form["label"] = "foo"

        form["credentials-0-identifier"] = "foo"
        form["credentials-0-secret"] = "bar"

        form.submit().follow()

        self.assertEqual(JWTSecret.objects.count(), 1)
        self.assertEqual(Applicatie.objects.count(), 1)

        applicatie = Applicatie.objects.get()
        credential = JWTSecret.objects.get()

        self.assertEqual(applicatie.client_ids, ["foo"])
        self.assertEqual(credential.identifier, "foo")
        self.assertEqual(credential.secret, "bar")
