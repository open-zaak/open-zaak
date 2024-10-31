# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import datetime
import os
import uuid
from base64 import b64encode
from unittest import skipIf

from django.test import override_settings

from drc_cmis.models import CMISConfig, UrlMapping
from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test import mock_service_oas_get
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...zaken.tests.utils import get_zaak_response
from ..models import EnkelvoudigInformatieObject, ObjectInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory


@require_cmis
@freeze_time("2018-06-27 12:12:12")
@override_settings(
    CMIS_ENABLED=True,
    CMIS_URL_MAPPING_ENABLED=True,
)
@skipIf(os.getenv("CMIS_BINDING") != "WEBSERVICE", "WEBSERVICE binding specific tests")
class URLMappingAPITests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_create_document_no_url_mapping(self):
        # Remove all available mappings
        UrlMapping.objects.all().delete()

        iot = InformatieObjectTypeFactory.create(concept=False)
        iot_url = f"http://testserver{reverse(iot)}"

        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": iot_url,
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(reverse(EnkelvoudigInformatieObject), content)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_list_documents_no_url_mapping(self):
        EnkelvoudigInformatieObjectFactory.create_batch(2)
        url = reverse("enkelvoudiginformatieobject-list")

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_retrieve_document_no_url_mapping(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(reverse(eio))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "CMIS-adapter could not shrink one of the URL fields.",
            response.data["detail"],
        )

    def test_update_document_no_url_mapping(self):
        iot1 = InformatieObjectTypeFactory.create(concept=False)
        iot2 = InformatieObjectTypeFactory.create(concept=False)

        eio = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iot1)

        eio_url = reverse(eio)
        eio_response = self.client.get(eio_url)
        eio_data = eio_response.data

        lock_response = self.client.post(f"{eio_url}/lock")
        self.assertEqual(lock_response.status_code, status.HTTP_200_OK)
        lock = lock_response.data["lock"]

        eio_data.update(
            {
                "informatieobjecttype": f"http://testserver{reverse(iot2)}",
                "lock": lock,
            }
        )
        del eio_data["integriteit"]
        del eio_data["ondertekening"]

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.put(eio_url, eio_data)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "CMIS-adapter could not shrink one of the URL fields.",
            response.data["detail"],
        )

    def test_destroy_document_no_url_mapping(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.delete(reverse(eio))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "CMIS-adapter could not shrink one of the URL fields.",
            response.data["detail"],
        )

    def test_create_gebruiksrechten_no_url_mapping(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            creatiedatum=datetime.date(2018, 12, 24)
        )
        eio_url = reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"uuid": eio.uuid},
        )

        eio_detail = self.client.get(eio_url)

        self.assertIsNone(eio_detail.json()["indicatieGebruiksrecht"])

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.post(
            reverse("gebruiksrechten-list"),
            {
                "informatieobject": f"http://testserver{eio_url}",
                "startdatum": "2018-12-24T00:00:00Z",
                "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
            },
        )

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_list_gebruiksrechten_no_url_mapping(self):
        for i in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = f"http://testserver{reverse(eio)}"
            GebruiksrechtenCMISFactory(informatieobject=eio_url)

        url = reverse("gebruiksrechten-list")

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_retrieve_gebruiksrechten_no_url_mapping(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(reverse(gebruiksrechten))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "CMIS-adapter could not shrink one of the URL fields.",
            response.data["detail"],
        )

    def test_destroy_gebruiksrechten_no_url_mapping(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.delete(reverse(gebruiksrechten))

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            "CMIS-adapter could not shrink one of the URL fields.",
            response.data["detail"],
        )

    def test_list_oio_no_url_mapping(self):
        config = CMISConfig.get_solo()
        UrlMapping.objects.create(
            long_pattern="https://externe.catalogus.nl",
            short_pattern="https://xcat.nl",
            config=config,
        )
        ServiceFactory.create(
            api_type=APITypes.zrc,
            api_root="https://externe.catalogus.nl/api/v1/",
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )

        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"

        mock_service_oas_get(
            self.adapter, "https://externe.catalogus.nl/api/v1/", APITypes.zrc
        )

        self.adapter.get(zaak, json=get_zaak_response(zaak, zaaktype))
        self.adapter.get(zaaktype, json=get_zaak_response(catalogus, zaaktype))

        for i in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            ObjectInformatieObject.objects.create(
                informatieobject=f"http://testserver{reverse(eio)}",
                zaak=zaak,
                object_type="zaak",
            )

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(reverse(ObjectInformatieObject))

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )

    def test_retrieve_oio_no_url_mapping(self):
        config = CMISConfig.get_solo()
        UrlMapping.objects.create(
            long_pattern="https://externe.catalogus.nl",
            short_pattern="https://xcat.nl",
            config=config,
        )
        ServiceFactory.create(
            api_type=APITypes.zrc,
            api_root="https://externe.catalogus.nl/api/v1/",
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )

        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"

        mock_service_oas_get(
            self.adapter, "https://externe.catalogus.nl/api/v1/", APITypes.zrc
        )

        self.adapter.get(zaak, json=get_zaak_response(zaak, zaaktype))
        self.adapter.get(zaaktype, json=get_zaak_response(catalogus, zaaktype))

        eio1 = EnkelvoudigInformatieObjectFactory.create()
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio1)}",
            zaak=zaak,
            object_type="zaak",
        )

        eio2 = EnkelvoudigInformatieObjectFactory.create()
        ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio2)}",
            zaak=zaak,
            object_type="zaak",
        )

        # Remove all available mappings
        UrlMapping.objects.all().delete()

        response = self.client.get(reverse(oio1))

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["detail"],
            "CMIS-adapter could not shrink one of the URL fields.",
        )
