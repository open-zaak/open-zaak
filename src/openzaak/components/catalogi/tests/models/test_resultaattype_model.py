# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import TestCase

import requests_mock
from dateutil.relativedelta import relativedelta
from vng_api_common.constants import Archiefnominatie

from ..factories import ResultaatTypeFactory, ZaakTypeFactory

RESULTAAT_URL = "https://ref.tst.vng.cloud/referentielijsten/api/v1/resultaten/{uuid}"


@requests_mock.Mocker()
class ResultaattypeTests(TestCase):
    def test_fill_in_default_archiefnominatie(self, m):
        """
        Assert that the archiefnominatie is filled in from the selectielijst
        """
        resultaat_url = RESULTAAT_URL.format(uuid=str(uuid.uuid4()))
        zaaktype = ZaakTypeFactory.create()
        resultaat = ResultaatTypeFactory.build(
            zaaktype=zaaktype, selectielijstklasse=resultaat_url, archiefnominatie=""
        )
        m.register_uri(
            "GET",
            resultaat_url,
            json={
                "url": resultaat_url,
                "procesType": resultaat.zaaktype.selectielijst_procestype,
                "waardering": Archiefnominatie.blijvend_bewaren,
            },
        )

        # save the thing, which should derive it from resultaat
        resultaat.save()

        resultaat.refresh_from_db()
        self.assertEqual(resultaat.archiefnominatie, Archiefnominatie.blijvend_bewaren)

    def test_explicitly_provided_archiefnominatie(self, m):
        """
        Assert that an explicit archiefnominatie is not filled in from the selectielijst
        """
        resultaat_url = RESULTAAT_URL.format(uuid=str(uuid.uuid4()))
        zaaktype = ZaakTypeFactory.create()
        resultaat = ResultaatTypeFactory.build(
            zaaktype=zaaktype,
            selectielijstklasse=resultaat_url,
            archiefnominatie=Archiefnominatie.vernietigen,
        )
        m.register_uri(
            "GET",
            resultaat_url,
            json={
                "url": resultaat_url,
                "procesType": resultaat.zaaktype.selectielijst_procestype,
                "waardering": Archiefnominatie.blijvend_bewaren,
            },
        )

        # save the thing, which should derive it from resultaat
        resultaat.save()

        resultaat.refresh_from_db()
        self.assertEqual(resultaat.archiefnominatie, Archiefnominatie.vernietigen)

    def test_fill_in_default_archiefactietermijn(self, m):
        """
        Assert that the archiefactietermijn is filled in from the selectielijst
        """
        resultaat_url = RESULTAAT_URL.format(uuid=str(uuid.uuid4()))
        zaaktype = ZaakTypeFactory.create()
        resultaat = ResultaatTypeFactory.build(
            zaaktype=zaaktype,
            selectielijstklasse=resultaat_url,
            archiefactietermijn=None,
        )
        m.register_uri(
            "GET",
            resultaat_url,
            json={
                "url": resultaat_url,
                "procesType": resultaat.zaaktype.selectielijst_procestype,
                "bewaartermijn": "P10Y",
            },
        )

        # save the thing, which should derive it from resultaat
        resultaat.save()

        resultaat.refresh_from_db()
        self.assertEqual(resultaat.archiefactietermijn, relativedelta(years=10))

    def test_explicitly_provided_bewaartermijn(self, m):
        """
        Assert that an explicit bewaartermijn is not filled in from the selectielijst
        """
        resultaat_url = RESULTAAT_URL.format(uuid=str(uuid.uuid4()))
        zaaktype = ZaakTypeFactory.create()
        resultaat = ResultaatTypeFactory.build(
            zaaktype=zaaktype,
            selectielijstklasse=resultaat_url,
            archiefactietermijn=relativedelta(years=5),
        )
        m.register_uri(
            "GET",
            resultaat_url,
            json={
                "url": resultaat_url,
                "procesType": resultaat.zaaktype.selectielijst_procestype,
                "bewaartermijn": "P10Y",
            },
        )

        # save the thing, which should derive it from resultaat
        resultaat.save()

        resultaat.refresh_from_db()
        self.assertEqual(resultaat.archiefactietermijn, relativedelta(years=5))
