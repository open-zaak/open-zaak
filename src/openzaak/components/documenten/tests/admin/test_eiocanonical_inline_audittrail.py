# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import tempfile

from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from privates.test import temp_private_root
from vng_api_common.audittrails.models import AuditTrail

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.models import EnkelvoudigInformatieObject

from ..factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from ..utils import get_operation_url


@temp_private_root()
@disable_admin_mfa()
class EioAdminInlineTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        cls.change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobjectcanonical_change",
            args=(cls.canonical.pk,),
        )

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)

    def assertEioAudittrail(self, audittrail):
        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}")
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name())

    def test_eio_delete(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            canonical=self.canonical, inhoud__filename="12321321.bin"
        )
        eio_url = get_operation_url("enkelvoudiginformatieobject_read", uuid=eio.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["enkelvoudiginformatieobject_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertEioAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "enkelvoudiginformatieobject")
        self.assertEqual(audittrail.resource_url, f"http://testserver{eio_url}")
        self.assertEqual(audittrail.resource_weergave, eio.unique_representation())
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{eio_url}")
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["identificatie"], str(eio.identificatie))

    def test_eio_change(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            canonical=self.canonical,
            identificatie="old",
            inhoud__filename="13213123123.bin",
        )
        eio_url = get_operation_url("enkelvoudiginformatieobject_read", uuid=eio.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["enkelvoudiginformatieobject_set-0-identificatie"] = "new"
        form.submit()

        eio.refresh_from_db()
        self.assertEqual(eio.identificatie, "new")

        audittrail = AuditTrail.objects.get()

        self.assertEioAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "enkelvoudiginformatieobject")
        self.assertEqual(audittrail.resource_url, f"http://testserver{eio_url}")
        self.assertEqual(audittrail.resource_weergave, eio.unique_representation())
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{eio_url}")

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["identificatie"], "old")
        self.assertEqual(new_data["identificatie"], "new")

    def test_eio_add(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        file = tempfile.NamedTemporaryFile()
        file.write(b"some content")
        file.seek(0)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["enkelvoudiginformatieobject_set-0-identificatie"] = "12345"
        form["enkelvoudiginformatieobject_set-0-bronorganisatie"] = "517439943"
        form["enkelvoudiginformatieobject_set-0-creatiedatum"] = "18-11-2019"
        form["enkelvoudiginformatieobject_set-0-titel"] = "some titel"
        form["enkelvoudiginformatieobject_set-0-auteur"] = "some author"
        form["enkelvoudiginformatieobject_set-0-_informatieobjecttype"] = (
            informatieobjecttype.id
        )
        form["enkelvoudiginformatieobject_set-0-taal"] = "Rus"
        form["enkelvoudiginformatieobject_set-0-inhoud"] = (file.name,)
        form["enkelvoudiginformatieobject_set-0-bestandsomvang"] = 12
        form["enkelvoudiginformatieobject_set-0-versie"] = "1"
        form.submit()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)

        eio = EnkelvoudigInformatieObject.objects.get()
        eio_url = get_operation_url("enkelvoudiginformatieobject_read", uuid=eio.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertEioAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "enkelvoudiginformatieobject")
        self.assertEqual(audittrail.resource_url, f"http://testserver{eio_url}")
        self.assertEqual(audittrail.resource_weergave, eio.unique_representation())
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{eio_url}")
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["identificatie"], "12345")
