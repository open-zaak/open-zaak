# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.utils.tests import AdminTestMixin

from ..factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from ..utils import get_operation_url


class EnkelvoudigInformatieObjectAdminTests(AdminTestMixin, TestCase):
    heeft_alle_autorisaties = True

    def _create_informatieobject(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")
        data = {
            "uuid": uuid.uuid4(),
            "_informatieobjecttype": informatieobjecttype.id,
            "canonical": canonical.id,
            "bronorganisatie": "517439943",
            "creatiedatum": "15-11-2019",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": SimpleUploadedFile("file_name.txt", b"file contents"),
            "beschrijving": "desc",
            "versie": 1,
        }

        self.client.post(add_url, data)

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)

        return EnkelvoudigInformatieObject.objects.get()

    def test_create_informatieobject(self):
        informatieobject = self._create_informatieobject()
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=informatieobject.uuid
        )

        self.assertEqual(AuditTrail.objects.count(), 1)

        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "enkelvoudiginformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, informatieobject.unique_representation()
        ),
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["beschrijving"], "desc")

    def test_change_informatieobject(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create(beschrijving="old")
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=informatieobject.uuid
        )
        change_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_change",
            args=(informatieobject.pk,),
        )
        data = {
            "uuid": informatieobject.uuid,
            "_informatieobjecttype": informatieobject.informatieobjecttype.id,
            "canonical": informatieobject.canonical.id,
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

        self.client.post(change_url, data)

        self.assertEqual(AuditTrail.objects.count(), 1)

        informatieobject.refresh_from_db()
        audittrail = AuditTrail.objects.get()

        self.assertEqual(audittrail.bron, "DRC")
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(audittrail.resource, "enkelvoudiginformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{informatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, informatieobject.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["beschrijving"], "old")
        self.assertEqual(new_data["beschrijving"], "new")

    def test_delete_informatieobject_action(self):
        informatieobject = self._create_informatieobject()

        self.assertEqual(AuditTrail.objects.count(), 1)

        change_list_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_changelist"
        )
        data = {
            "action": "delete_selected",
            "_selected_action": [informatieobject.id],
            "post": "yes",
        }

        self.client.post(change_list_url, data)

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)

    def test_delete_informatieobject(self):
        informatieobject = self._create_informatieobject()

        self.assertEqual(AuditTrail.objects.count(), 1)

        delete_url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete",
            args=(informatieobject.pk,),
        )
        data = {"post": "yes"}

        self.client.post(delete_url, data)

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 0)
        self.assertEqual(AuditTrail.objects.count(), 0)
