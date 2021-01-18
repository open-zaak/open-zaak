# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from datetime import timedelta

from django.urls import reverse

import requests_mock
from dateutil.relativedelta import relativedelta
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.selectielijst.tests import (
    mock_oas_get,
    mock_resource_get,
    mock_resource_list,
)
from openzaak.selectielijst.tests.mixins import ReferentieLijstServiceMixin
from openzaak.utils.tests import ClearCachesMixin

from ..factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


@requests_mock.Mocker()
class ReadonlyAdminTests(ReferentieLijstServiceMixin, ClearCachesMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_readonly_zaaktype(self, m):
        """
        check that in case of published zaaktype only "datum_einde_geldigheid" field is editable
        """
        procestype_url = (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        mock_oas_get(m)
        mock_resource_get(m, "procestypen", procestype_url)

        zaaktype = ZaakTypeFactory.create(
            concept=False,
            zaaktype_omschrijving="test",
            vertrouwelijkheidaanduiding="openbaar",
            trefwoorden=["test1", "test2"],
            verantwoordingsrelatie=["bla"],
            selectielijst_procestype=procestype_url,
            doorlooptijd_behandeling=timedelta(days=10),
            producten_of_diensten=["http://example.com/1", "http://example.com/2"],
        )
        url = reverse("admin:catalogi_zaaktype_change", args=(zaaktype.pk,))

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        zaaktype_fields = [
            f.name
            for f in zaaktype._meta.get_fields()
            if f.name != "datum_einde_geldigheid"
        ]

        self.assertEqual("datum_einde_geldigheid" in form_fields, True)
        for field in zaaktype_fields:
            self.assertEqual(field in form_fields, False)

        # check custom formatting
        procestype = response.html.find(class_="field-selectielijst_procestype").div.div
        self.assertEqual(procestype.text, "1 - Instellen en inrichten organisatie")
        behandeling = response.html.find(
            class_="field-doorlooptijd_behandeling"
        ).div.div
        self.assertEqual(behandeling.text, "10 days")
        producten_of_diensten = response.html.find(
            class_="field-producten_of_diensten"
        ).div.div
        self.assertEqual(len(producten_of_diensten.find_all("a")), 2)

    def test_readonly_besluittype(self, m):
        """
        check that in case of published besluittype only "datum_einde_geldigheid" field is editable
        """
        mock_oas_get(m)

        besluittype = BesluitTypeFactory.create(concept=False)
        url = reverse("admin:catalogi_besluittype_change", args=(besluittype.pk,))

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        besluittype_fields = [
            f.name
            for f in besluittype._meta.get_fields()
            if f.name != "datum_einde_geldigheid"
        ]

        self.assertEqual("datum_einde_geldigheid" in form_fields, True)
        for field in besluittype_fields:
            self.assertEqual(field in form_fields, False)

    def test_readonly_informatieobjecttype(self, m):
        """
        check that in case of published informatieobjecttype only "datum_einde_geldigheid" field is editable
        """
        mock_oas_get(m)

        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        url = reverse(
            "admin:catalogi_informatieobjecttype_change",
            args=(informatieobjecttype.pk,),
        )

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        informatieobjecttype_fields = [
            f.name
            for f in informatieobjecttype._meta.get_fields()
            if f.name != "datum_einde_geldigheid"
        ]

        self.assertEqual("datum_einde_geldigheid" in form_fields, True)
        for field in informatieobjecttype_fields:
            self.assertEqual(field in form_fields, False)

    def test_readonly_statustype(self, m):
        """
        check that in case of published zaaktype, statustype page is readonly
        """
        mock_oas_get(m)

        statustype = StatusTypeFactory.create(zaaktype__concept=False)
        url = reverse("admin:catalogi_statustype_change", args=(statustype.pk,))

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        statustype_fields = [f.name for f in statustype._meta.get_fields()]

        for field in statustype_fields:
            self.assertEqual(field in form_fields, False)

    def test_readonly_zaaktypeinformatieobjecttype(self, m):
        """
        check that in case of published zaaktype, zaaktypeinformatieobjecttype page is readonly
        """
        mock_oas_get(m)

        ztiot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = reverse(
            "admin:catalogi_zaaktypeinformatieobjecttype_change", args=(ztiot.pk,)
        )

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        ztiot_fields = [f.name for f in ztiot._meta.get_fields()]

        for field in ztiot_fields:
            self.assertEqual(field in form_fields, False)

    def test_readonly_resultaattype(self, m):
        """
        check that in case of published zaaktype, resultaattype page is readonly
        """
        selectielijst_api = "https://selectielijst.openzaak.nl/api/v1/"
        procestype_url = (
            f"{selectielijst_api}procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        )
        resultaat_url = (
            f"{selectielijst_api}resultaten/cc5ae4e3-a9e6-4386-bcee-46be4986a829"
        )
        omschrijving_url = (
            "https://referentielijsten-api.vng.cloud/api/v1/"
            "resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7"
        )

        mock_oas_get(m)
        mock_resource_list(m, "resultaattypeomschrijvingen")
        mock_resource_list(m, "resultaten")
        mock_resource_get(m, "procestypen", procestype_url)
        mock_resource_get(m, "resultaten", resultaat_url)
        mock_resource_get(m, "resultaattypeomschrijvingen", omschrijving_url)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__selectielijst_procestype=procestype_url,
            selectielijstklasse=resultaat_url,
            resultaattypeomschrijving=omschrijving_url,
            archiefactietermijn=relativedelta(years=5),
        )
        url = reverse("admin:catalogi_resultaattype_change", args=(resultaattype.pk,))

        response = self.app.get(url)

        form = response.form
        form_fields = list(form.fields.keys())
        resultaattype_fields = [f.name for f in resultaattype._meta.get_fields()]

        for field in resultaattype_fields:
            self.assertEqual(field in form_fields, False)

        # check custom formatting
        selectielijstklasse = response.html.find(
            class_="field-selectielijstklasse"
        ).div.div
        self.assertEqual(selectielijstklasse.text, "1.1 - Ingericht - vernietigen")
        omschrijving = response.html.find(
            class_="field-resultaattypeomschrijving"
        ).div.div
        self.assertEqual(omschrijving.text, "Afgewezen")
        archiefactietermijn = response.html.find(
            class_="field-archiefactietermijn"
        ).div.div
        self.assertEqual(archiefactietermijn.text, "5 years")
