# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.validators import IsImmutableValidator

from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from ..models import ZaakInformatieObject
from .factories import ResultaatFactory, ZaakInformatieObjectFactory
from .utils import isodatetime


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectValidationCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):

    heeft_alle_autorisaties = True

    def test_informatieobject_create(self):
        site = Site.objects.get_current()
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {"zaak": f"http://{site.domain}{zaak_url}", "informatieobject": io_url,},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_informatieobject_fails(self):
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

        self.create_zaak_besluit_services()
        zaak = self.create_zaak()

        zio = ZaakInformatieObjectFactory.create(
            informatieobject=io_url,
            informatieobject__informatieobjecttype=io.informatieobjecttype,
            zaak=zaak,
        )
        zio_url = reverse(zio)

        response = self.client.patch(zio_url, {"informatieobject": io_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        validation_error = get_validation_errors(response, "informatieobject")
        self.assertEqual(validation_error["code"], IsImmutableValidator.code)


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class FilterValidationCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    heeft_alle_autorisaties = True

    def test_validate_zaakinformatieobject_unknown_query_params(self):
        self.create_zaak_besluit_services()
        for counter in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()
            self.adapter.get(eio_url, json=serialise_eio(eio, eio_url))
            zaak = self.create_zaak()
            ZaakInformatieObjectFactory.create(informatieobject=eio_url, zaak=zaak)

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class StatusValidationCMISTests(JWTAuthMixin, APICMISTestCase, OioMixin):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create()
        StatusTypeFactory.create(zaaktype=cls.zaaktype)
        statustype_end = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_end_url = reverse(statustype_end)

    def test_status_with_informatieobject_lock(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        io.canonical.lock_document(io.uuid)
        self.adapter.get(io_url, json=serialise_eio(io, io_url, locked=True))
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
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(**{"zaaktype": self.zaaktype})
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(indicatie_gebruiksrecht=None)
        io_url = io.get_url()
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
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
