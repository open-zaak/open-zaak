# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from datetime import date

from django.test import tag
from django.utils.translation import gettext as _

from dateutil.relativedelta import relativedelta
from freezegun.api import freeze_time
from log_outgoing_requests.models import OutgoingRequestsLogConfig
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
)
from vng_api_common.tests import reverse_lazy

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
from openzaak.components.zaken.tests.utils import utcdatetime
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse


@freeze_time("2025-04-04")
class HoofdzaakAfsluitingTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    status_list_url = reverse_lazy("zaken:status-list")

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

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(zaaktype=self.int_zaaktype)
        StatusFactory.create(
            zaak=self.zaak,
            statustype=self.int_statustype1,
            datum_status_gezet=utcdatetime(2024, 4, 4),
        )
        ResultaatFactory.create(zaak=self.zaak, resultaattype=self.int_resultaattype)

        self.zaak_url = reverse("zaken:zaak-detail", kwargs={"uuid": self.zaak.uuid})

        # Clear singleton model caches to keep query count
        # the same between running whole test class & tests separately.
        OutgoingRequestsLogConfig.clear_cache()

    def test_deelzaak(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)

        ResultaatFactory.create(
            zaak=deelzaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=10),
                archiefnominatie=Archiefnominatie.vernietigen,
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )

        deelzaak_url = reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid})

        with self.subTest("close deelzaak"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": deelzaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 16, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            deelzaak.refresh_from_db()

            self.assertIsNone(deelzaak.archiefnominatie)
            self.assertIsNone(deelzaak.archiefactiedatum)
            self.assertIsNone(deelzaak.startdatum_bewaartermijn)

        with self.subTest("reopen deelzaak"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": deelzaak_url,
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 25, 16, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            deelzaak.refresh_from_db()

            self.assertIsNone(deelzaak.archiefnominatie)
            self.assertIsNone(deelzaak.archiefactiedatum)
            self.assertIsNone(deelzaak.startdatum_bewaartermijn)

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

    def test_zaak_afsluiten_with_closed_deelzaak_with_internal_deelzaak_catalogi(self):
        deelzaak_same_termijn = ZaakFactory.create(
            zaaktype=self.int_zaaktype, hoofdzaak=self.zaak
        )
        deelzaak_different_termijn = ZaakFactory.create(
            zaaktype=self.int_zaaktype, hoofdzaak=self.zaak
        )
        StatusFactory.create(
            zaak=deelzaak_same_termijn,
            statustype=self.int_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(
            zaak=deelzaak_same_termijn,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=10),
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )
        StatusFactory.create(
            zaak=deelzaak_different_termijn,
            statustype=self.int_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 5),
        )
        ResultaatFactory.create(
            zaak=deelzaak_different_termijn,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=5),
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
        deelzaak_same_termijn.refresh_from_db()
        deelzaak_different_termijn.refresh_from_db()

        # Assert that the same brondatum/startdatum_bewaartermijn is used to calculate
        # the archiefactiedatum, but that the termijn can differ
        self.assertTrue(
            self.zaak.startdatum_bewaartermijn
            == deelzaak_same_termijn.startdatum_bewaartermijn
            == deelzaak_different_termijn.startdatum_bewaartermijn
        )
        self.assertEqual(
            self.zaak.archiefactiedatum,
            self.zaak.startdatum_bewaartermijn + relativedelta(years=10),
        )
        self.assertEqual(
            deelzaak_same_termijn.archiefactiedatum,
            self.zaak.startdatum_bewaartermijn + relativedelta(years=10),
        )
        self.assertEqual(
            deelzaak_different_termijn.archiefactiedatum,
            self.zaak.startdatum_bewaartermijn + relativedelta(years=5),
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
                    "zaak": reverse(
                        "zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid}
                    ),
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
                    "zaak": reverse(
                        "zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid}
                    ),
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 7).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["invalid_params"][0]["code"], "hoofdzaak-closed"
            )

    def _generate_deelzaken(self, n: int):
        for _ in range(n):
            deelzaak = ZaakFactory.create(
                zaaktype=self.int_zaaktype,
                hoofdzaak=self.zaak,
            )
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

    def test_queries_with_no_deelzaken(self):
        with self.assertNumQueries(61):
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
        self._generate_deelzaken(1)
        """
        Query count when closing a hoofdzaak with one internal deelzaak.

        Compared to the "no deelzaken" case, the additional queries are:

        (1) 58: check whether the hoofdzaak has deelzaken
        (2) 59: update archiving fields for the deelzaak(s)
        (3) 60: release savepoint
        """
        with self.assertNumQueries(64):
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
        """
        A Deelzaak with an internal catalogi has 5 extra queries compared to no deelzaken.

        (1) 27: deelzaak reopen filter query
        (2) 28: deelzaak eindstatus filter query
        (3) 41: savepoint transaction management
        (4) 52: archiving update
        (5) 64: savepoint release
        """
        self._generate_deelzaken(10)
        with self.assertNumQueries(64):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_queries_with_many_deelzaken(self):
        self._generate_deelzaken(20)

        with self.assertNumQueries(64):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": self.zaak_url,
                    "statustype": f"http://testserver{self.int_statustype2_url}",
                    "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_close_and_reopen_hoofdzaak(self):
        deelzaak1 = ZaakFactory.create(
            zaaktype=self.int_zaaktype,
            hoofdzaak=self.zaak,
        )
        deelzaak2 = ZaakFactory.create(
            zaaktype=self.int_zaaktype,
            hoofdzaak=self.zaak,
        )

        ResultaatFactory.create(
            zaak=deelzaak1,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=20),
                archiefnominatie=Archiefnominatie.vernietigen,
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )
        ResultaatFactory.create(
            zaak=deelzaak2,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefactietermijn=relativedelta(years=20),
                archiefnominatie=Archiefnominatie.vernietigen,
                brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak,
            ),
        )

        # close first deelzaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak1.uuid}),
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # close second deelzaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak2.uuid}),
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # close hoofdzaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # reopen hoofdzaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype1_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.zaak.refresh_from_db()
        deelzaak1.refresh_from_db()
        deelzaak2.refresh_from_db()

        self.assertIsNone(self.zaak.archiefnominatie)
        self.assertIsNone(self.zaak.archiefactiedatum)
        self.assertIsNone(self.zaak.startdatum_bewaartermijn)

        self.assertIsNone(deelzaak1.archiefnominatie)
        self.assertIsNone(deelzaak1.archiefactiedatum)
        self.assertIsNone(deelzaak1.startdatum_bewaartermijn)

        self.assertIsNone(deelzaak2.archiefnominatie)
        self.assertIsNone(deelzaak2.archiefactiedatum)
        self.assertIsNone(deelzaak2.startdatum_bewaartermijn)

    @tag("gh-2448")
    def test_close_hoofdzaak_with_deelzaak_with_blijvend_bewaren_archiefnominatie(self):
        self.zaak.resultaat.delete()
        ResultaatFactory.create(
            zaak=self.zaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                selectielijstklasse="",
                archiefactietermijn=None,
                archiefnominatie=Archiefnominatie.blijvend_bewaren,
            ),
        )

        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)
        ResultaatFactory.create(
            zaak=deelzaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                archiefnominatie=Archiefnominatie.blijvend_bewaren,
                brondatum_archiefprocedure_afleidingswijze=(
                    BrondatumArchiefprocedureAfleidingswijze.hoofdzaak
                ),
            ),
        )

        # close the deelzaak first
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid}),
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 5).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # close the hoofdzaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": self.zaak_url,
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.zaak.refresh_from_db()
        deelzaak.refresh_from_db()

        self.assertEqual(self.zaak.einddatum, date(2024, 4, 6))
        self.assertEqual(self.zaak.archiefnominatie, Archiefnominatie.blijvend_bewaren)
        self.assertIsNone(self.zaak.archiefactiedatum)
        self.assertIsNone(self.zaak.startdatum_bewaartermijn)

        self.assertEqual(deelzaak.einddatum, date(2024, 4, 5))
        self.assertEqual(deelzaak.archiefnominatie, Archiefnominatie.blijvend_bewaren)
        self.assertIsNone(deelzaak.archiefactiedatum)
        self.assertIsNone(deelzaak.startdatum_bewaartermijn)

    @tag("gh-2448")
    def test_close_zaak_afleidingswijze_hoofdzaak_without_hoofdzaak(self):
        self.zaak.resultaat.delete()
        ResultaatFactory.create(
            zaak=self.zaak,
            resultaattype=ResultaatTypeFactory.create(
                zaaktype=self.int_zaaktype,
                selectielijstklasse="",
                archiefnominatie=Archiefnominatie.vernietigen,
                archiefactietermijn=relativedelta(years=10),
                brondatum_archiefprocedure_afleidingswijze=(
                    BrondatumArchiefprocedureAfleidingswijze.hoofdzaak
                ),
            ),
        )

        self.assertIsNone(self.zaak.hoofdzaak)

        # close the zaak
        response = self.client.post(
            self.status_list_url,
            {
                "zaak": f"http://testserver{self.zaak_url}",
                "statustype": f"http://testserver{self.int_statustype2_url}",
                "datumStatusGezet": utcdatetime(2024, 4, 6).isoformat(),
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(
            response.data["invalid_params"][0]["code"], "archiefactiedatum-error"
        )
        self.assertEqual(
            response.data["invalid_params"][0]["reason"],
            _(
                "De archiefactiedatum kan niet bepaald worden, omdat de afleidingswijze `{hoofdzaak}` "
                "gebruikt wordt, maar de zaak geen hoofdzaak heeft."
            ).format(hoofdzaak=BrondatumArchiefprocedureAfleidingswijze.hoofdzaak),
        )

    @tag("gh-2098")
    def test_change_deelzaak_status_without_resultaat(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)

        deelzaak_url = reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid})

        with self.subTest("change deelzaak status"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": deelzaak_url,
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 16, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            deelzaak.refresh_from_db()
            self.assertIsNone(deelzaak.archiefnominatie)
            self.assertIsNone(deelzaak.einddatum)

    @tag("gh-2098")
    def test_reopen_deelzaak_status_without_resultaat(self):
        deelzaak = ZaakFactory.create(zaaktype=self.int_zaaktype, hoofdzaak=self.zaak)

        deelzaak_url = reverse("zaken:zaak-detail", kwargs={"uuid": deelzaak.uuid})

        StatusFactory.create(
            zaak=deelzaak,
            statustype=self.int_statustype2,
            datum_status_gezet=utcdatetime(2024, 4, 4),
        )

        with self.subTest("reopen deelzaak"):
            response = self.client.post(
                self.status_list_url,
                {
                    "zaak": deelzaak_url,
                    "statustype": f"http://testserver{self.int_statustype1_url}",
                    "datumStatusGezet": utcdatetime(
                        2018, 10, 22, 16, 00, 00
                    ).isoformat(),
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deelzaak.refresh_from_db()
        self.assertIsNone(deelzaak.archiefnominatie)
        self.assertIsNone(deelzaak.einddatum)
