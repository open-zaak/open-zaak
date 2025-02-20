# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin, get_eio_response

from .factories import ResultaatFactory, ZaakFactory, ZaakInformatieObjectFactory
from .utils import isodatetime


@override_settings(ALLOWED_HOSTS=["testserver"])
@tag("external-urls")
@requests_mock.Mocker()
class ExternalDocumentsAPITests(JWTAuthMixin, APITestCase):
    """
    Test validation with remote documents involved.
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://external.catalogus.nl/", api_type=APITypes.ztc
        )
        ServiceFactory.create(
            api_root="https://external.nl/documenten/", api_type=APITypes.drc
        )
        cls.zaaktype = ZaakTypeFactory.create()
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_end = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.zaaktype_url = reverse(cls.zaaktype)
        cls.statustype_url = reverse(cls.statustype)
        cls.statustype_end_url = reverse(cls.statustype_end)

    def test_eindstatus_with_informatieobject_unlocked(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(
                REMOTE_DOCUMENT,
                locked=False,
                indicatieGebruiksrecht=False,
            ),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_eindstatus_with_informatieobject_lock(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(REMOTE_DOCUMENT, locked=True),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "informatieobject-locked")

    def test_status_with_informatieobject_indicatie_gebruiksrecht_null(self, m):
        REMOTE_DOCUMENT = "https://external.nl/documenten/123"
        m.get(
            REMOTE_DOCUMENT,
            json=get_eio_response(REMOTE_DOCUMENT, indicatieGebruiksrecht=None),
        )
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=REMOTE_DOCUMENT)
        resultaattype = ResultaatTypeFactory.create(
            archiefactietermijn="P10Y",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            zaaktype=self.zaaktype,
        )
        ResultaatFactory.create(zaak=zaak, resultaattype=resultaattype)
        list_url = reverse("status-list")

        response = self.client.post(
            list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_end_url}",
                "datumStatusGezet": isodatetime(2019, 7, 22, 13, 00, 00),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "indicatiegebruiksrecht-unset")
