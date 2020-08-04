# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.urls import reverse

from django_webtest import WebTest
from webtest import Upload

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory

from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


class EnkelvoudigInformatieObjectAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def test_add_informatieobject_page(self):
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        self.assertEqual(response.status_code, 200)

    def test_create_informatieobject_save(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.form

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 200)
