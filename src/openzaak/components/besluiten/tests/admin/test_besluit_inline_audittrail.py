from django.urls import reverse

from django_webtest import WebTest
from vng_api_common.audittrails.models import AuditTrail

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.documenten.tests.utils import (
    get_operation_url as get_operation_url_doc,
)
from openzaak.utils.tests import AdminTestMixin

from ..factories import BesluitFactory, BesluitInformatieObjectFactory
from ..utils import get_operation_url


class BesluitAdminInlineTests(AdminTestMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.besluit = BesluitFactory.create()

        super().setUpTestData()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)
        self.besluit_url = get_operation_url("besluit_read", uuid=self.besluit.uuid)
        self.change_url = reverse(
            "admin:besluiten_besluit_change", args=(self.besluit.pk,)
        )

    def assertBesluitAudittrail(self, audittrail):
        self.assertEqual(audittrail.bron, "BRC")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(
            audittrail.hoofd_object, f"http://testserver{self.besluit_url}"
        ),

    def test_bio_delete(self):
        bio = BesluitInformatieObjectFactory.create(besluit=self.besluit)
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["besluitinformatieobject_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(BesluitInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertBesluitAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["url"], f"http://testserver{bio_url}")

    def test_bio_change(self):
        (
            informatieobject_old,
            informatieobject_new,
        ) = EnkelvoudigInformatieObjectFactory.create_batch(2)
        bio = BesluitInformatieObjectFactory.create(
            besluit=self.besluit, informatieobject=informatieobject_old.canonical
        )
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form[
            "besluitinformatieobject_set-0-_informatieobject"
        ] = informatieobject_new.canonical.id
        form.submit()

        bio.refresh_from_db()
        self.assertEqual(bio._informatieobject, informatieobject_new.canonical)

        audittrail = AuditTrail.objects.get()

        self.assertBesluitAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "besluitinformatieobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        informatieobject_old_url = get_operation_url_doc(
            "enkelvoudiginformatieobject_read", uuid=informatieobject_old.uuid
        )
        informatieobject_new_url = get_operation_url_doc(
            "enkelvoudiginformatieobject_read", uuid=informatieobject_new.uuid
        )
        self.assertEqual(
            old_data["informatieobject"], f"http://testserver{informatieobject_old_url}"
        )
        self.assertEqual(
            new_data["informatieobject"], f"http://testserver{informatieobject_new_url}"
        )

    def test_bio_add(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create()

        data = {
            "uuid": self.besluit.uuid,
            "_besluittype": self.besluit._besluittype.id,
            "verantwoordelijke_organisatie": self.besluit.verantwoordelijke_organisatie,
            "datum": self.besluit.datum,
            "ingangsdatum": "15-11-2019",
            "toelichting": self.besluit.toelichting,
            "besluitinformatieobject_set-TOTAL_FORMS": 1,
            "besluitinformatieobject_set-INITIAL_FORMS": 0,
            "besluitinformatieobject_set-MIN_NUM_FORMS": 0,
            "besluitinformatieobject_set-MAX_NUM_FORMS": 1000,
            "besluitinformatieobject_set-0-besluit": self.besluit.id,
            "besluitinformatieobject_set-0-_informatieobject": informatieobject.canonical.id,
        }

        self.client.post(self.change_url, data)

        self.assertEqual(BesluitInformatieObject.objects.count(), 1)

        bio = BesluitInformatieObject.objects.get()
        bio_url = get_operation_url("besluitinformatieobject_read", uuid=bio.uuid)
        audittrail = AuditTrail.objects.get(resource="besluitinformatieobject")

        self.assertBesluitAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource_url, f"http://testserver{bio_url}"),
        self.assertEqual(audittrail.resource_weergave, bio.unique_representation())
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["url"], f"http://testserver{bio_url}")
