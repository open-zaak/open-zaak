# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

import os
import uuid
from unittest import skipIf

from django.test import override_settings, tag
from django.urls import reverse

from maykin_2fa.test import disable_admin_mfa
from rest_framework import status
from vng_api_common import tests

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import AdminTestMixin, APICMISTestCase, require_cmis

from ..factories import EnkelvoudigInformatieObjectFactory


@require_cmis
@disable_admin_mfa()
@override_settings(CMIS_ENABLED=True)
class EnkelvoudigInformatieObjectCMISAdminTest(AdminTestMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_create_eio_is_forbidden_when_cmis_enabled(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = tests.reverse(informatieobjecttype)

        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        data = {
            "uuid": uuid.uuid4(),
            "informatieobjecttype": informatieobjecttype_url,
            "bronorganisatie": "517439943",
            "creatiedatum": "15-11-2019",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "beschrijving": "desc",
            "versie": 1,
        }

        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_eio_is_forbidden_when_cmis_enabled(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(informatieobject.uuid,),
        )
        data = {
            "uuid": informatieobject.uuid,
            "_informatieobjecttype": informatieobject.informatieobjecttype.id,
            "bronorganisatie": informatieobject.bronorganisatie,
            "creatiedatum": informatieobject.creatiedatum,
            "titel": informatieobject.titel,
            "auteur": informatieobject.auteur,
            "formaat": informatieobject.formaat,
            "taal": informatieobject.taal,
            "bestandsnaam": informatieobject.bestandsnaam,
            "inhoud": informatieobject.inhoud,
            "beschrijving": "new",
            "versie": informatieobject.versie,
        }

        response = self.client.post(change_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_eio_is_forbidden_when_cmis_enabled(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")

        delete_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete",
            args=(informatieobject.uuid,),
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        response = self.client.post(delete_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @tag("pickme")
    @skipIf(
        os.getenv("CMIS_BINDING") == "WEBSERVICE",
        "Webservice CMIS binding does not support file content URLs",
    )
    def test_eio_detail(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")

        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(informatieobject.uuid,),
        )

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)

    def test_view_documents_cmis(self):
        changelist_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_changelist"
        )

        response = self.client.get(changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "admin/documenten/cmis.html")
        self.assertNotIn("cl", response.context)
