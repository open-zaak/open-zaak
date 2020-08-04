# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test value of vertrouwelijkheidaanduiding while creating EnkelvoudigInformatieObject

See:
https://github.com/VNG-Realisatie/gemma-zaken/issues/609
"""
from base64 import b64encode

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import JWTAuthMixin


class US609TestCase(TypeCheckMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_vertrouwelijkheidaanduiding_derived(self):
        """
        Assert that the default vertrouwelijkheidaanduiding is set
        from informatieobjecttype
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            concept=False,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.post(
            url,
            {
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
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )

    def test_vertrouwelijkheidaanduiding_explicit(self):
        """
        Assert the explicit set of vertrouwelijkheidaanduiding
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            concept=False,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.post(
            url,
            {
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
                "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )
