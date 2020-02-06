import uuid

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from vng_api_common import tests

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import AdminTestMixin, APICMISTestCase

from ..factories import EnkelvoudigInformatieObjectFactory


@override_settings(CMIS_ENABLED=True)
class EnkelvoudigInformatieObjectCMISAdminTest(AdminTestMixin, APICMISTestCase):
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
