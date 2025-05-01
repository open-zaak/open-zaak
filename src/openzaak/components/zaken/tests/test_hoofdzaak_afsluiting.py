# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.test import override_settings, tag

import requests_mock
from dateutil.relativedelta import relativedelta
from freezegun.api import freeze_time
from log_outgoing_requests.models import OutgoingRequestsLogConfig
from mozilla_django_oidc_db.models import OpenIDConnectConfig
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import reverse, reverse_lazy
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.factories import (
    ResultaatFactory,
    StatusFactory,
    ZaakFactory,
)
from openzaak.components.zaken.tests.utils import (
    get_resultaattype_response,
    get_statustype_response,
    get_zaaktype_response,
    utcdatetime,
)
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get


@freeze_time("2025-04-04")
class HoofdzaakAfsluitingTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    status_list_url = reverse_lazy("status-list")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.int_zaaktype = ZaakTypeFactory.create(concept=False)

        cls.int_statustype1 = StatusTypeFactory.create(zaaktype=cls.int_zaaktype)
        cls.int_statustype1_url = reverse(cls.int_statustype1)

        cls.int_statustype2 = StatusTypeFactory.create(zaaktype=cls.int_zaaktype)
        cls.int_statustype2_url = reverse(cls.int_statustype2)

        cls.int_resultaattype = ResultaatTypeFactory.create(
            zaaktype=cls.int_zaaktype,
            archiefactietermijn=relativedelta(years=10),
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        base_url = "https://externe.catalogus.nl/api/v1"
        cls.ext_catalogus = (
            f"{base_url}/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        )
        cls.ext_zaaktype = f"{base_url}/zaaktypen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        cls.ext_statustype1 = (
            f"{base_url}/statustypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        cls.ext_statustype2 = (
            f"{base_url}/statustypen/b71f72ef-198d-44d8-af64-ae1932df123b"
        )
        cls.ext_resultaattype = (
            f"{base_url}/resultaattypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        )

        cls.mocker = requests_mock.Mocker()
        cls.mocker.start()

        mock_ztc_oas_get(cls.mocker)
        cls.mocker.get(
            cls.ext_zaaktype,
            json=get_zaaktype_response(cls.ext_catalogus, cls.ext_zaaktype),
        )
        cls.mocker.get(
            cls.ext_statustype1,
            json=get_statustype_response(cls.ext_statustype1, cls.ext_zaaktype),
        )
        cls.mocker.get(
            cls.ext_statustype2,
            json=get_statustype_response(
                cls.ext_statustype2, cls.ext_zaaktype, isEindstatus=True
            ),
        )
        cls.mocker.get(
            cls.ext_resultaattype,
            json=get_resultaattype_response(
                cls.ext_resultaattype,
                cls.ext_zaaktype,
                brondatumArchiefprocedure={
                    "afleidingswijze": "hoofdzaak",
                },
            ),
        )

        cls.addClassCleanup(cls.mocker.stop)

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(zaaktype=self.int_zaaktype)
        StatusFactory.create(
            zaak=self.zaak,
            statustype=self.int_statustype1,
            datum_status_gezet=utcdatetime(2024, 4, 4),
        )
        ResultaatFactory.create(zaak=self.zaak, resultaattype=self.int_resultaattype)

        self.zaak_url = reverse("zaak-detail", kwargs={"uuid": self.zaak.uuid})

    def tearDown(self):
        """
        Clears singleton model caches to keep query count
        the same between running whole test class & tests separately.
        """
        OpenIDConnectConfig.clear_cache()
        OutgoingRequestsLogConfig.clear_cache()

    def test_validation_with_internal_deelzaak_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)

        with self.subTest("deelzaak without status"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 10, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "deelzaken-not-closed"
            )

        with self.subTest("deelzaak with open status"):
            StatusFactory.create(
                zaak=deelzaak,
                statustype=self.int_statustype1,
                datum_status_gezet=utcdatetime(2024, 4, 4),
            )

            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 10, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "deelzaken-not-closed"
            )

        with self.subTest("deelzaak with end status without resultaat"):
            StatusFactory.create(
                zaak=deelzaak,
                statustype=self.int_statustype2,
                datum_status_gezet=utcdatetime(2024, 4, 5),
            )
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 10, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"],
                "deelzaak-resultaat-does-not-exist",
            )

    def test_validation_with_internal_deelzaak_catalogi_multiple(self):
        deelzaak1 = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)

        StatusFactory.create(
            zaak=deelzaak1,
            statustype=self.int_statustype1,
            datum_status_gezet=utcdatetime(2024, 4, 4),
        )

        int_zaaktype = ZaakTypeFactory.create(concept=False)
        StatusTypeFactory.create(zaaktype=int_zaaktype)
        StatusTypeFactory.create(zaaktype=int_zaaktype)
        deelzaak2 = ZaakFactory.create(zaaktype=int_zaaktype, hoofdzaak=self.zaak)

        StatusFactory.create(
            zaak=deelzaak2,
            statustype=StatusTypeFactory.create(zaaktype=int_zaaktype),
            datum_status_gezet=utcdatetime(2024, 4, 4),
        )

        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2018, 10, 22, 10, 00, 00).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["invalid_params"][0]["code"], "deelzaken-not-closed"
        )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_validation_with_external_deelzaak_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.ext_zaaktype, hoofdzaak=self.zaak)

        with self.subTest("deelzaak without status"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 10, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "deelzaken-not-closed"
            )

        with self.subTest("deelzaak with open status"):
            StatusFactory.create(
                zaak=deelzaak,
                statustype=self.ext_statustype1,
                datum_status_gezet=utcdatetime(2024, 4, 4),
            )
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "deelzaken-not-closed"
            )

        with self.subTest("deelzaak with end status without resultaat"):
            StatusFactory.create(
                zaak=deelzaak,
                statustype=self.ext_statustype2,
                datum_status_gezet=utcdatetime(2024, 4, 5),
            )
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"],
                "deelzaak-resultaat-does-not-exist",
            )

    def test_zaak_afsluiten_with_closed_deelzaak_with_internal_deelzaak_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)
        StatusFactory.create(
            zaak=deelzaak,
            statustype=self.int_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(
            zaak=deelzaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=20),
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )

        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.zaak.refresh_from_db()
        deelzaak.refresh_from_db()
        self.assertEqual(
            self.zaak.archiefactiedatum, self.zaak.einddatum + relativedelta(years=10)
        )
        self.assertEqual(
            deelzaak.archiefactiedatum, self.zaak.einddatum + relativedelta(years=10)
        )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_zaak_afsluiten_with_closed_deelzaak_with_external_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.ext_zaaktype, hoofdzaak=self.zaak)
        StatusFactory.create(
            zaak=deelzaak,
            statustype=self.ext_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(zaak=deelzaak, resultaattype=self.ext_resultaattype)

        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.zaak.refresh_from_db()
        deelzaak.refresh_from_db()
        self.assertEqual(
            self.zaak.archiefactiedatum, self.zaak.einddatum + relativedelta(years=10)
        )
        self.assertEqual(
            deelzaak.archiefactiedatum, self.zaak.einddatum + relativedelta(years=10)
        )

    def test_reopen_deelzaak_with_internal_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)
        StatusFactory.create(
            zaak=deelzaak,
            statustype=self.int_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(
            zaak=deelzaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=20),
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )

        with self.subTest("opened hoofdzaak"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": reverse("zaak-detail", kwargs={"uuid": deelzaak.uuid}),
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("closed hoofdzaak"):
            StatusFactory.create(
                zaak=self.zaak,
                statustype=self.int_statustype2,
                datum_status_gezet=utcdatetime(2024, 4, 5),
            )

            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": reverse("zaak-detail", kwargs={"uuid": deelzaak.uuid}),
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 7).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "hoofdzaak-closed"
            )

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_reopen_deelzaak_with_external_catalogi(self):
        deelzaak = ZaakFactory.create(zaaktype=self.ext_zaaktype, hoofdzaak=self.zaak)
        StatusFactory.create(
            zaak=deelzaak,
            statustype=self.ext_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(zaak=deelzaak, resultaattype=self.ext_resultaattype)

        with self.subTest("opened hoofdzaak"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": reverse("zaak-detail", kwargs={"uuid": deelzaak.uuid}),
                    "statustype": self.ext_statustype1,
                    "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("closed hoofdzaak"):
            StatusFactory.create(
                zaak=self.zaak,
                statustype=self.int_statustype2,
                datum_status_gezet=utcdatetime(2024, 4, 5),
            )

            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": reverse("zaak-detail", kwargs={"uuid": deelzaak.uuid}),
                    "statustype": self.ext_statustype1,
                    "datumStatusGezet": utcdatetime(2024, 4, 7).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "hoofdzaak-closed"
            )

    def _generate_deelzaken(self, n: int, internal=True):
        for i in range(n):
            deelzaak = ZaakFactory.create(
                zaaktype=self.int_zaaktype if internal else self.ext_zaaktype,
                hoofdzaak=self.zaak,
            )
            StatusFactory.create(
                zaak=deelzaak,
                statustype=self.int_statustype2 if internal else self.ext_statustype2,
                datum_status_gezet=utcdatetime(2024, 4, 5),
            )
            ResultaatFactory.create(
                zaak=deelzaak,
                resultaattype=(
                    ResultaatTypeFactory.create(
                        zaaktype=self.int_zaaktype,
                        archiefactietermijn=relativedelta(years=20),
                        brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
                    )
                    if internal
                    else self.ext_resultaattype
                ),
            )

    def test_queries_with_no_deelzaken(self):
        with self.assertNumQueries(67):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_queries_with_one_deelzaak_with_internal_catalogi(self):
        self._generate_deelzaken(1, True)
        """
        An Deelzaak with an external catalogi has 5 extra queries compared to no deelzaken.

        (1) 42: deelzaak reopen filter query
        (2) 43: deelzaak eindstatus filter query
        (3) 44: cursor from exist()
        (4) 66: update the deelzaak
        (5) 67: cursor from exist()

        """
        with self.assertNumQueries(72):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_queries_with_one_deelzaak_with_external_catalogi(self):
        """
        An Deelzaak with an external catalogi has 16 extra queries compared to a deelzaak with an internal catalogi.

        (1) 45: Lookup the current status
        (2-3) 46-47: select from zgw_consumers_service
        (3-7) 48-51: outgoing requests log (Done once)
        (8) 75: lookup the deelzaak resultaat
        (9-10)  76-77: select from zgw_consumers_service
        (11) 78: update the deelzaak
        (12-16) 79-83 select related zaak data

        """
        self._generate_deelzaken(1, False)
        with self.assertNumQueries(88):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_queries_with_many_deelzaken_with_internal_catalogi(self):
        self._generate_deelzaken(10, True)
        with self.assertNumQueries(72):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_queries_with_many_deelzaken_with_external_catalogi(self):
        """
        A single deelzaak with external catalogi has 16 extra queries over an internal catalogi.
        The 4 queries for outgoing request logging are done once which means every deelzaak
        (with an external catalogi) adds 12 queries.
        72 + 4 + (10*12) = 196
        """
        self._generate_deelzaken(10, False)
        with self.assertNumQueries(196):  # TODO
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @tag("external-urls")
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_queries_with_many_deelzaken(self):
        self._generate_deelzaken(10, True)
        self._generate_deelzaken(10, False)
        with self.assertNumQueries(196):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
