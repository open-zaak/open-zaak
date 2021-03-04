# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import (
    mock_oas_get,
    mock_resource_get,
    mock_resource_list,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.utils.tests import ClearCachesMixin

from ..factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)


@requests_mock.Mocker()
class NotificationAdminTests(ReferentieLijstServiceMixin, ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.allowed_years = [2017, 2020]
        config.save()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    @patch("vng_api_common.notifications.viewsets.NotificationMixin.notify")
    def test_zaaktype_notify(self, m, notify_mock):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)

        zaaktype = ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)
        form = response.forms["zaaktype_form"]
        form.submit("_save")

        notify_mock.assert_called_once()

    @patch("vng_api_common.notifications.viewsets.NotificationMixin.notify")
    def test_besluit_notify(self, m, notify_mock):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)

        besluit = BesluitTypeFactory.create(concept=True, omschrijving="test")
        url = reverse("admin:catalogi_besluittype_change", args=(besluit.pk,))

        response = self.app.get(url)
        form = response.forms["besluittype_form"]
        form.submit("_save")

        notify_mock.assert_called_once()

    @patch("vng_api_common.notifications.viewsets.NotificationMixin.notify")
    def test_informatieobject_notify(self, m, notify_mock):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)

        informatieobject = InformatieObjectTypeFactory.create(
            concept=True, vertrouwelijkheidaanduiding="openbaar"
        )
        url = reverse(
            "admin:catalogi_informatieobjecttype_change", args=(informatieobject.pk,)
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]
        form.submit("_save")

        notify_mock.assert_called_once()

    @patch("vng_api_common.notifications.viewsets.NotificationMixin.notify")
    def test_catalogus_notify(self, m, notify_mock):
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_list(m, "procestypen")
        mock_resource_get(m, "procestypen", procestype_url)

        catalogus = CatalogusFactory.create(rsin="100000009")

        ZaakTypeFactory.create(
            concept=True,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            catalogus=catalogus,
        )

        InformatieObjectTypeFactory.create(
            concept=True, vertrouwelijkheidaanduiding="openbaar", catalogus=catalogus,
        )

        BesluitTypeFactory.create(
            concept=True, omschrijving="test", catalogus=catalogus,
        )

        url = reverse("admin:catalogi_catalogus_change", args=(catalogus.pk,))

        response = self.app.get(url)
        form = response.forms["catalogus_form"]
        form.submit("_save")

        notify_mock.assert_called()
