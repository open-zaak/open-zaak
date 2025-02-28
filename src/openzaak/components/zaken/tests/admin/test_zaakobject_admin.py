# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    ZaakObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import ZaakObject
from openzaak.tests.utils import AdminTestMixin

from ..factories import ZaakFactory, ZaakObjectFactory


@disable_admin_mfa()
class ZaakObjectAdminTests(AdminTestMixin, WebTest):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_valid_create_zaakobject(self):
        zaak = ZaakFactory.create()
        zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=zaak.zaaktype)

        get_response = self.app.get(reverse("admin:zaken_zaakobject_add"))
        form = get_response.form
        form["zaak"] = zaak.id
        form["object"] = "http://example.com/adres/1"
        form["object_type"] = "adres"
        form["_zaakobjecttype"] = zaakobjecttype.id
        form.submit()

        self.assertEqual(ZaakObject.objects.count(), 1)
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak.id, zaak.id)
        self.assertEqual(zaakobject.object, "http://example.com/adres/1")
        self.assertEqual(zaakobject.object_type, "adres")
        self.assertEqual(zaakobject.zaakobjecttype, zaakobjecttype)
        self.assertEqual(zaakobject.zaakobjecttype.zaaktype, zaak.zaaktype)

    def test_invalid_create_zaakobject(self):
        catalogus = CatalogusFactory.create()
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus)
        zaak = ZaakFactory.create(zaaktype=zaaktype1)
        zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=zaaktype2)

        get_response = self.app.get(reverse("admin:zaken_zaakobject_add"))
        form = get_response.form
        form["zaak"] = zaak.id
        form["object"] = "http://example.com/adres/1"
        form["object_type"] = "adres"
        form["_zaakobjecttype"] = zaakobjecttype.id
        response = form.submit()

        self.assertContains(
            response, "De referentie hoort niet bij het zaaktype van de zaak."
        )
        self.assertEqual(ZaakObject.objects.count(), 0)

    def test_valid_update_zaakobject(self):
        zaak = ZaakFactory.create()
        zaakobject = ZaakObjectFactory.create(
            object="http://example.com/adres/1",
            object_type="adres",
            zaak=zaak,
        )
        zaakobjecttype = ZaakObjectTypeFactory.create(zaaktype=zaak.zaaktype)

        get_response = self.app.get(
            reverse("admin:zaken_zaakobject_change", args=(zaakobject.pk,))
        )
        form = get_response.form
        form["object"] = "http://example.com/adres/2"
        form["_zaakobjecttype"] = zaakobjecttype.id
        form.submit()

        self.assertEqual(ZaakObject.objects.count(), 1)
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak.id, zaak.id)
        self.assertEqual(zaakobject.object, "http://example.com/adres/2")
        self.assertEqual(zaakobject.object_type, "adres")
        self.assertEqual(zaakobject.zaakobjecttype, zaakobjecttype)
        self.assertEqual(zaakobject.zaakobjecttype.zaaktype, zaak.zaaktype)
