# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""
import base64
from datetime import date
from urllib.parse import urlparse

from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ..models import EnkelvoudigInformatieObject
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from .utils import get_operation_url


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class US39TestCase(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_create_enkelvoudiginformatieobject(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
            "identificatie": "AMS20180701001",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "text_extra.txt",
            "auteur": "ANONIEM",
            "formaat": "text/plain",
            "taal": "dut",
            "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(eio.identificatie, "AMS20180701001")
        self.assertEqual(eio.creatiedatum, date(2018, 7, 1))

        download_url = urlparse(response.data["inhoud"])

        self.assertEqual(
            download_url.path,
            get_operation_url("enkelvoudiginformatieobject_download", uuid=eio.uuid),
        )

    def test_read_detail_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue().decode("utf-8"), "some data")

    def test_list_file(self):
        EnkelvoudigInformatieObjectCanonicalFactory.create()
        eio = EnkelvoudigInformatieObject.objects.get()
        list_url = get_operation_url("enkelvoudiginformatieobject_list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["results"]
        download_url = reverse(
            "enkelvoudiginformatieobject-download", kwargs={"uuid": eio.uuid}
        )

        self.assertEqual(
            data[0]["inhoud"], f"http://testserver{download_url}?versie={eio.versie}",
        )
