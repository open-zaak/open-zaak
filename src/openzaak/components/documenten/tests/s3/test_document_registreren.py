# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid
from base64 import b64encode
from unittest.mock import patch

from django.test import override_settings, tag

from maykin_common.vcr import VCRMixin
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.zaken.tests.factories import (
    StatusFactory,
    ZaakFactory,
)
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils import build_absolute_url

from ...models import EnkelvoudigInformatieObject
from ...storage import documenten_storage
from .mixins import S3torageMixin, upload_to


@tag("gh-2282", "s3-storage", "convenience-endpoints")
@override_settings(OPENZAAK_DOMAIN="testserver", SITE_DOMAIN="testserver")
@patch("privates.fields.PrivateMediaFileField.generate_filename", upload_to)
class DocumentRegistrerenAuthTests(VCRMixin, S3torageMixin, JWTAuthMixin, APITestCase):
    url = reverse_lazy("registreerdocument-list")
    heeft_alle_autorisaties = True

    def test_register_document(self):
        iotype = InformatieObjectTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=iotype
        )

        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = reverse(zaak)

        status_url = reverse(StatusFactory.create(zaak=zaak))

        # Ensure the same UUID is used to make sure the VCR cassette matches
        with patch(
            "openzaak.components.documenten.models._uuid.uuid4",
            return_value=uuid.UUID("7534a3b5-975b-4d87-bcf4-7f4073fd527d"),
        ):
            response = self.client.post(
                self.url,
                {
                    "enkelvoudiginformatieobject": {
                        "identificatie": uuid.uuid4().hex,
                        "bronorganisatie": "159351741",
                        "creatiedatum": "2025-01-01",
                        "titel": "detailed summary",
                        "auteur": "test_auteur",
                        "formaat": "txt",
                        "taal": "eng",
                        "bestandsnaam": "test_register_document.txt",
                        "inhoud": b64encode(b"some file content").decode("utf-8"),
                        "link": "http://een.link",
                        "beschrijving": "test_beschrijving",
                        "informatieobjecttype": build_absolute_url(reverse(iotype)),
                        "vertrouwelijkheidaanduiding": "geheim",
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
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()

        self.assertTrue(documenten_storage.exists(eio.inhoud.name))
        self.assertEqual(eio.inhoud.read(), b"some file content")
