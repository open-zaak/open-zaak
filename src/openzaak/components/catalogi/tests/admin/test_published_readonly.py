from django.urls import reverse

import requests_mock
from django_webtest import WebTest

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.selectielijst.tests import mock_oas_get, mock_resource_get
from openzaak.utils.tests import ClearCachesMixin

from ..factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


@requests_mock.Mocker()
class ReadonlyAdminTests(ClearCachesMixin, WebTest):
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
            "https://referentielijsten-api.vng.cloud/api/v1/"
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
