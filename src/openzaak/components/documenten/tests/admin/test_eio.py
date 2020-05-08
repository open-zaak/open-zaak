import uuid

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django_webtest import WebTest
from vng_api_common import tests
from webtest import Upload
from rest_framework import status

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import AdminTestMixin, APITestCaseCMIS

from ..factories import EnkelvoudigInformatieObjectCanonicalFactory, EnkelvoudigInformatieObjectFactory


@override_settings(CMIS_ENABLED=False)
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
        form["inhoud"] = Upload("stuff.txt", b"")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 200)


@override_settings(CMIS_ENABLED=True)
class EnkelvoudigInformatieObjectCMISAdminTest(AdminTestMixin, APITestCaseCMIS):
    heeft_alle_autorisaties = True

    def test_create_eio_is_forbidden_when_cmis_enabled(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = tests.reverse(informatieobjecttype)

        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        data = {
            "uuid": uuid.uuid4(),
            "informatieobjecttype": informatieobjecttype_url,
            "bronorganisatie": "517439943",
            "creatiedatum": "15-11-2019",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "beschrijving": "desc",
            "versie": 1,
        }

        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_eio_is_forbidden_when_cmis_enabled(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(informatieobject.uuid,),
        )
        data = {
            "uuid": informatieobject.uuid,
            "_informatieobjecttype": informatieobject.informatieobjecttype.id,
            "bronorganisatie": informatieobject.bronorganisatie,
            "creatiedatum": informatieobject.creatiedatum,
            "titel": informatieobject.titel,
            "auteur": informatieobject.auteur,
            "formaat": informatieobject.formaat,
            "taal": informatieobject.taal,
            "bestandsnaam": informatieobject.bestandsnaam,
            "inhoud": informatieobject.inhoud,
            "beschrijving": "new",
            "versie": informatieobject.versie,
        }

        response = self.client.post(change_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_eio_is_forbidden_when_cmis_enabled(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")

        delete_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete",
            args=(informatieobject.uuid,),
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        response = self.client.post(delete_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
