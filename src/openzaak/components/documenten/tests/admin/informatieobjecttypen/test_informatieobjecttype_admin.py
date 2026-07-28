# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.test import override_settings, tag
from django.urls import reverse as django_reverse, reverse_lazy
from django.utils.translation import gettext as _, ngettext_lazy

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.models import (
    InformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils.admin import AdminTestMixin
from openzaak.utils.urls import reverse


@disable_admin_mfa()
class IoTypePublishAdminTests(AdminTestMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        cls.catalogus = CatalogusFactory.create()
        cls.url = reverse_lazy("admin:catalogi_informatieobjecttype_changelist")
        cls.query_params = {"catalogus_id__exact": cls.catalogus.pk}

    def test_publish_selected_success(self):
        iotype1, iotype2 = InformatieObjectTypeFactory.create_batch(
            2, catalogus=self.catalogus
        )

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [iotype1.pk]

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                ngettext_lazy(
                    "%d object has been published successfully",
                    "%d objects has been published successfully",
                    1,
                )
                % 1
            ],
        )

        iotype1.refresh_from_db()
        self.assertFalse(iotype1.concept)

        iotype2.refresh_from_db()
        self.assertTrue(iotype2.concept)

    def test_publish_already_selected(self):
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus, concept=False
        )

        response = self.app.get(self.url, self.query_params)

        form = response.forms["changelist-form"]
        form["action"] = "publish_selected"
        form["_selected_action"] = [iotype.pk]

        response = form.submit()

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                ngettext_lazy(
                    "%d object is already published",
                    "%d objects are already published",
                    1,
                )
                % 1
            ],
        )

        iotype.refresh_from_db()
        self.assertFalse(iotype.concept)

    def test_change_page_publish(self):
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus, concept=True
        )

        url = django_reverse(
            "admin:catalogi_informatieobjecttype_change", args=(iotype.pk,)
        )

        response = self.app.get(url)
        response = response.forms["informatieobjecttype_form"].submit("_publish")

        iotype.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(iotype.concept)

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(messages, [_("The resource has been published successfully!")])

    def test_change_page_publish_overlap(self):
        InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            concept=False,
            omschrijving="enter text here",
            datum_begin_geldigheid="2020-10-20",
        )

        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus,
            concept=True,
            omschrijving="enter text here",
            datum_begin_geldigheid="2020-10-30",
        )

        url = django_reverse(
            "admin:catalogi_informatieobjecttype_change", args=(iotype.pk,)
        )

        response = self.app.get(url)
        form = response.forms["informatieobjecttype_form"]
        response = form.submit("_publish")

        iotype.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(iotype.concept)

        messages = [str(m) for m in response.follow().context["messages"]]
        self.assertEqual(
            messages,
            [
                "Informatieobjecttype versies (dezelfde omschrijving) mogen geen "
                "overlappende geldigheid hebben."
            ],
        )


@disable_admin_mfa()
class CreateIotypeTests(NotificationsConfigMixin, AdminTestMixin, WebTest):
    url = reverse_lazy("admin:catalogi_informatieobjecttype_add")

    @override_settings(NOTIFICATIONS_DISABLED=False, LOG_NOTIFICATIONS_IN_DB=False)
    @freeze_time("2022-01-01")
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_create_notification_actie(self, mock_notif):
        catalogus = CatalogusFactory.create()

        response = self.app.get(self.url)

        form = response.forms["informatieobjecttype_form"]
        form["omschrijving"] = "test"
        form["vertrouwelijkheidaanduiding"] = "openbaar"
        form["catalogus"] = catalogus.id
        form["datum_begin_geldigheid"] = "2021-10-20"
        form["informatieobjectcategorie"] = "main"

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)

        iotype = InformatieObjectType.objects.get()
        iotype_url = reverse(
            iotype,
            namespace="documenten",
        )
        catalogus_url = reverse(
            "catalogi:catalogus-detail", kwargs={"uuid": catalogus.uuid, "version": 1}
        )
        mock_notif.assert_called_with(
            {
                "aanmaakdatum": "2022-01-01T00:00:00Z",
                "actie": "create",
                "hoofdObject": f"http://testserver{iotype_url}",
                "kanaal": "informatieobjecttypen",
                "resource": "informatieobjecttype",
                "resourceUrl": f"http://testserver{iotype_url}",
                "kenmerken": {
                    "catalogus": f"http://testserver{catalogus_url}",
                },
            },
            None,
        )


@tag("gh-1877")
@disable_admin_mfa()
class InformatieObjectTypeDeleteAdminTests(AdminTestMixin, WebTest):
    def test_delete_published_informatieobjecttype_not_allowed_if_documenten_related(
        self,
    ):
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False
        )

        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=non_concept_informatieobjecttype
        )

        admin_url = django_reverse(
            "admin:catalogi_informatieobjecttype_delete",
            args=(non_concept_informatieobjecttype.id,),
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(
            _("Informatieobjecttype kan niet worden verwijderd"), response.text
        )
        self.assertIn(
            _("vereist het verwijderen van de volgende gerelateerde objecten"),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(InformatieObjectType.objects.count(), 1)

    def test_bulk_delete_published_informatieobjecttypen_not_allowed_if_documenten_related(
        self,
    ):
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False
        )

        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=non_concept_informatieobjecttype
        )

        admin_url = django_reverse("admin:catalogi_informatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_informatieobjecttype.id,
            non_concept_informatieobjecttype.id,
        ]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )
        # Delete is not allowed
        self.assertIn(
            _("Informatieobjecttypen kan niet worden verwijderd"), response.text
        )
        self.assertIn(
            _(
                "vereist het verwijderen van de volgende beschermde gerelateerde objecten"
            ),
            response.text,
        )
        # Delete confirmation form should not be present
        self.assertNotIn(1, response.forms)
        self.assertEqual(InformatieObjectType.objects.count(), 2)

    def test_delete_published_informatieobjecttype_allowed_if_no_documenten_related(
        self,
    ):
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False
        )

        admin_url = django_reverse(
            "admin:catalogi_informatieobjecttype_delete",
            args=(non_concept_informatieobjecttype.id,),
        )

        response = self.app.get(admin_url)

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # informatieobjecttype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_bulk_delete_published_informatieobjecttypen_allowed_if_no_documenten_related(
        self,
    ):
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)
        non_concept_informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False
        )

        admin_url = django_reverse("admin:catalogi_informatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_informatieobjecttype.id,
            non_concept_informatieobjecttype.id,
        ]

        response = form.submit()

        # warning about deleting published types should be present on confirmation page
        self.assertIsNotNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both Besluittypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_delete_concept_informatieobjecttype_allowed_if_no_documenten_related(self):
        concept_informatieobjecttype = InformatieObjectTypeFactory.create(concept=True)

        admin_url = django_reverse(
            "admin:catalogi_informatieobjecttype_delete",
            args=(concept_informatieobjecttype.id,),
        )

        response = self.app.get(admin_url)

        # no warning, because all informatieobjecttypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]

        response = form.submit()

        # informatieobjecttype is successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_bulk_delete_concept_informatieobjecttypen_allowed_if_no_documenten_related(
        self,
    ):
        concept_informatieobjecttype1 = InformatieObjectTypeFactory.create(concept=True)
        concept_informatieobjecttype2 = InformatieObjectTypeFactory.create(concept=True)

        admin_url = django_reverse("admin:catalogi_informatieobjecttype_changelist")
        form = self.app.get(admin_url).forms["changelist-form"]
        form["action"] = "delete_selected"
        form["_selected_action"] = [
            concept_informatieobjecttype1.id,
            concept_informatieobjecttype2.id,
        ]

        response = form.submit()

        # no warning, because all informatieobjecttypen are concepts
        self.assertIsNone(
            response.html.find("li", {"id": "deleting-published-types-warning"})
        )

        form = response.forms[1]
        form["action"] = "delete_selected"
        form["post"] = "yes"

        response = form.submit()

        # Both informatieobjecttypen are successfully deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InformatieObjectType.objects.exists())
