import uuid
from base64 import b64encode

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_CREATE
from openzaak.components.zaken.tests.factories import StatusFactory, ZaakFactory
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
class ReservedDocumentTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("document_registreren-list")
    # heeft_alle_autorisaties = True
    scopes = [SCOPE_DOCUMENTEN_AANMAKEN]
    component = ComponentTypes.drc

    def test_register_document(self):
        zaak = ZaakFactory()
        zaak_url = reverse(zaak)

        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=informatieobjecttype
        )

        status_url = reverse(StatusFactory.create(zaak=zaak))

        content = {
            "enkelvoudiginformatieobject": {
                "identificatie": uuid.uuid4().hex,
                "bronorganisatie": "159351741",
                "creatiedatum": "2025-01-01",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                "vertrouwelijkheidaanduiding": "openbaar",
                "verschijningsvorm": "Vorm A",
                "trefwoorden": ["some", "other"],
            },
            "zaakinformatieobject": {
                "zaak": f"http://testserver{zaak_url}",
                "titel": "string",
                "beschrijving": "string",
                "vernietigingsdatum": "2019-08-24T14:15:22Z",
                "status": f"http://testserver{status_url}",
            },
        }

        # Send to the API
        response = self.client.post(self.url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # # Test database
        # stored_object = EnkelvoudigInformatieObject.objects.get()
        #
        # self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        # self.assertEqual(stored_object.identificatie, content["identificatie"])
        # self.assertEqual(stored_object.bronorganisatie, "159351741")
        # self.assertEqual(stored_object.creatiedatum, date(2018, 6, 27))
        # self.assertEqual(stored_object.titel, "detailed summary")
        # self.assertEqual(stored_object.auteur, "test_auteur")
        # self.assertEqual(stored_object.formaat, "txt")
        # self.assertEqual(stored_object.taal, "eng")
        # self.assertEqual(stored_object.versie, 1)
        # self.assertAlmostEqual(stored_object.begin_registratie, timezone.now())
        # self.assertEqual(stored_object.bestandsnaam, "dummy.txt")
        # self.assertEqual(stored_object.inhoud.read(), b"some file content")
        # self.assertEqual(stored_object.link, "http://een.link")
        # self.assertEqual(stored_object.beschrijving, "test_beschrijving")
        # self.assertEqual(stored_object.informatieobjecttype, informatieobjecttype)
        # self.assertEqual(stored_object.vertrouwelijkheidaanduiding, "openbaar")
        # self.assertEqual(stored_object.verschijningsvorm, "Vorm A")
        # self.assertEqual(stored_object.trefwoorden, ["some", "other"])
        #
        # expected_url = reverse(stored_object)
        # expected_file_url = get_operation_url(
        #     "enkelvoudiginformatieobject_download", uuid=stored_object.uuid
        # )
        #
        # expected_response = content.copy()
        # expected_response.update(
        #     {
        #         "url": f"http://testserver{expected_url}",
        #         "inhoud": f"http://testserver{expected_file_url}?versie=1",
        #         "versie": 1,
        #         "bestandsdelen": [],
        #         "beginRegistratie": stored_object.begin_registratie.isoformat().replace(
        #             "+00:00", "Z"
        #         ),
        #         "vertrouwelijkheidaanduiding": "openbaar",
        #         "bestandsomvang": stored_object.inhoud.size,
        #         "integriteit": {"algoritme": "", "waarde": "", "datum": None},
        #         "ontvangstdatum": None,
        #         "verzenddatum": None,
        #         "ondertekening": {"soort": "", "datum": None},
        #         "indicatieGebruiksrecht": None,
        #         "status": "",
        #         "locked": False,
        #         "lock": "",
        #         "verschijningsvorm": "Vorm A",
        #     }
        # )
        #
        # response_data = response.json()
        # self.assertEqual(
        #     sorted(response_data.keys()), sorted(expected_response.keys())
        # )
        #
        # for key in response_data:
        #     with self.subTest(field=key):
        #         self.assertEqual(response_data[key], expected_response[key])
