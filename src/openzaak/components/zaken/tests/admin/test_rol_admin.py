# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    RolTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import Rol
from openzaak.tests.utils import AdminTestMixin

from ..factories import RolFactory, ZaakFactory


@disable_admin_mfa()
class RolAdminTests(AdminTestMixin, WebTest):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.app.set_user(self.user)

    def test_valid_create_rol(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        get_response = self.app.get(reverse("admin:zaken_rol_add"))

        form = get_response.form
        form["zaak"] = zaak.id
        form["_roltype"] = roltype.id
        form["betrokkene_type"] = "natuurlijk_persoon"
        form["betrokkene"] = "http://example.com/betrokkene/1"
        form["roltoelichting"] = "desc"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()
        self.assertEqual(rol.roltype, roltype)
        self.assertEqual(rol.zaak, zaak)
        self.assertEqual(rol.roltype.zaaktype, rol.zaak.zaaktype)

    def test_invalid_create_rol(self):
        # check_zaaktype validation
        catalogus = CatalogusFactory.create()
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus)
        zaak = ZaakFactory.create(zaaktype=zaaktype1)
        roltype = RolTypeFactory.create(zaaktype=zaaktype2)

        self.assertEqual(Rol.objects.count(), 0)

        get_response = self.app.get(reverse("admin:zaken_rol_add"))
        form = get_response.form
        form["zaak"] = zaak.id
        form["_roltype"] = roltype.id
        form["betrokkene_type"] = "natuurlijk_persoon"
        form["betrokkene"] = "http://example.com/betrokkene/1"
        form["roltoelichting"] = "desc"
        response = form.submit()

        self.assertContains(
            response, "De referentie hoort niet bij het zaaktype van de zaak."
        )
        self.assertEqual(Rol.objects.count(), 0)

    def test_valid_update_rol(self):
        zaak = ZaakFactory.create()
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        rol = RolFactory.create(roltoelichting="old", roltype=roltype, zaak=zaak)

        get_response = self.app.get(reverse("admin:zaken_rol_change", args=(rol.pk,)))

        form = get_response.form
        form["roltoelichting"] = "new"
        form.submit()

        rol = Rol.objects.get()
        self.assertEqual(rol.roltype, roltype)
        self.assertEqual(rol.zaak, zaak)

        self.assertEqual(rol.roltype.zaaktype, rol.zaak.zaaktype)
