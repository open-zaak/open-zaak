# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings
from django.test import override_settings

from rest_framework import status
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ..models import ZaakInformatieObject
from .factories import ResultaatFactory, ZaakFactory, ZaakInformatieObjectFactory
from .utils import isodatetime


@require_cmis
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectValidationCMISTests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    @override_settings(OPENZAAK_DOMAIN="testserver")
    def test_informatieobject_create(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {
                "zaak": f"http://{settings.OPENZAAK_DOMAIN}{zaak_url}",
                "informatieobject": io_url,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_informatieobject_fails(self):
        iot = InformatieObjectTypeFactory.create()

        # Create 2 documents with the same IOT
        io_1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False, informatieobjecttype=iot
        )
        io_1_url = f"http://testserver{reverse(io_1)}"

        io_2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False, informatieobjecttype=iot
        )
        io_2_url = f"http://testserver{reverse(io_2)}"

        # Relate a zaak to one of the documents
        zio = ZaakInformatieObjectFactory.create(
            informatieobject=io_1_url,
        )
        zio_url = reverse(zio)

        # Attempt to replace the document related to the zaak with another document
        response = self.client.patch(zio_url, {"informatieobject": io_2_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "informatieobject")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class FilterValidationCMISTests(JWTAuthMixin, APICMISTestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_validate_zaakinformatieobject_unknown_query_params(self):
        for counter in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()
            ZaakInformatieObjectFactory.create(informatieobject=eio_url)

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


@require_cmis
@override_settings(CMIS_ENABLED=True)
class StatusValidationCMISTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create()
        StatusTypeFactory.create(zaaktype=cls.zaaktype)
        statustype_end = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_end_url = reverse(statustype_end)

    def test_status_with_informatieobject_lock(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        io.canonical.lock_document(io.uuid)

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

    def test_status_with_informatieobject_indicatie_gebruiksrecht_null(self):
        zaak = ZaakFactory.create(**{"zaaktype": self.zaaktype})
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(indicatie_gebruiksrecht=None)
        io_url = io.get_url()

        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
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
