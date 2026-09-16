# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from datetime import date, timedelta

from openzaak.tests.utils import TestMigrations
from openzaak.utils.urls import reverse

class TestMoveApplicationsMigrations(TestMigrations):
    migrate_from = "0017_remove_old_application_fk_on_catalogiautorisatie"
    migrate_to = "0018_move_auth_admin_permissions_to_new_models"
    app = "autorisaties"

    def setUpBeforeMigration(self, apps):
        self.ApplicatieOld = apps.get_model("authorizations", "Applicatie")
        self.AutorisatieOld = apps.get_model("authorizations", "Autorisatie")

        self.ApplicatieNew = apps.get_model("autorisaties", "Applicatie")
        self.AutorisatieNew = apps.get_model("autorisaties", "Autorisatie")


        self.ZaakType = apps.get_model("catalogi", "ZaakType")
        self.BesluitType = apps.get_model("catalogi", "BesluitType")
        self.InformatieObjectType = apps.get_model("catalogi", "InformatieObjectType")
        self.Catalogus = apps.get_model("catalogi", "Catalogus")

        ContentType = apps.get_model("contenttypes", "ContentType")
        Permission = apps.get_model("auth", "Permission")
        User = apps.get_model("accounts", "User")

        self.old_applicatie_ct = ContentType.objects.get_for_model(self.ApplicatieOld)
        self.old_autorisatie_ct = ContentType.objects.get_for_model(self.AutorisatieOld)

        self.new_applicatie_ct = ContentType.objects.get_for_model(self.ApplicatieNew)
        self.new_autorisatie_ct = ContentType.objects.get_for_model(self.AutorisatieNew)

        old_perms = Permission.objects.filter(content_type__in=[self.old_applicatie_ct, self.old_autorisatie_ct])

        self.user = User.objects.create(username="test")
        self.user.user_permissions.set(old_perms)

        self.group = self.user.groups.create(name="test")
        self.group.permissions.set(old_perms)

    def test_user_permissions(self):
        perms = self.user.user_permissions
        self.assertEqual(perms.count(), 8)
        self.assertEqual(perms.filter(content_type=self.old_applicatie_ct).count(), 0)
        self.assertEqual(perms.filter(content_type=self.old_autorisatie_ct).count(), 0)
        self.assertEqual(perms.filter(content_type=self.new_applicatie_ct).count(), 4)
        self.assertEqual(perms.filter(content_type=self.new_autorisatie_ct).count(), 4)


        add_applicatie = perms.get(codename="add_applicatie", content_type=self.new_applicatie_ct)
        change_applicatie = perms.get(codename="change_applicatie", content_type=self.new_applicatie_ct)
        view_applicatie = perms.get(codename="view_applicatie", content_type=self.new_applicatie_ct)
        delete_applicatie = perms.get(codename="delete_applicatie", content_type=self.new_applicatie_ct)

        self.assertEqual(perms.contains(add_applicatie), True)
        self.assertEqual(perms.contains(change_applicatie), True)
        self.assertEqual(perms.contains(view_applicatie), True)
        self.assertEqual(perms.contains(delete_applicatie), True)

        add_autorisatie = perms.get(codename="add_autorisatie", content_type=self.new_autorisatie_ct)
        change_autorisatie = perms.get(codename="change_autorisatie", content_type=self.new_autorisatie_ct)
        view_autorisatie = perms.get(codename="view_autorisatie", content_type=self.new_autorisatie_ct)
        delete_autorisatie = perms.get(codename="delete_autorisatie", content_type=self.new_autorisatie_ct)

        self.assertEqual(perms.contains(add_autorisatie), True)
        self.assertEqual(perms.contains(change_autorisatie), True)
        self.assertEqual(perms.contains(view_autorisatie), True)
        self.assertEqual(perms.contains(delete_autorisatie), True)

    def test_group_permissions(self):
        perms = self.group.permissions
        self.assertEqual(perms.count(), 8)
        self.assertEqual(perms.filter(content_type=self.old_applicatie_ct).count(), 0)
        self.assertEqual(perms.filter(content_type=self.old_autorisatie_ct).count(), 0)
        self.assertEqual(perms.filter(content_type=self.new_applicatie_ct).count(), 4)
        self.assertEqual(perms.filter(content_type=self.new_autorisatie_ct).count(), 4)

        add_applicatie = perms.get(codename="add_applicatie", content_type=self.new_applicatie_ct)
        change_applicatie = perms.get(codename="change_applicatie", content_type=self.new_applicatie_ct)
        view_applicatie = perms.get(codename="view_applicatie", content_type=self.new_applicatie_ct)
        delete_applicatie = perms.get(codename="delete_applicatie", content_type=self.new_applicatie_ct)

        self.assertEqual(perms.contains(add_applicatie), True)
        self.assertEqual(perms.contains(change_applicatie), True)
        self.assertEqual(perms.contains(view_applicatie), True)
        self.assertEqual(perms.contains(delete_applicatie), True)

        add_autorisatie = perms.get(codename="add_autorisatie", content_type=self.new_autorisatie_ct)
        change_autorisatie = perms.get(codename="change_autorisatie", content_type=self.new_autorisatie_ct)
        view_autorisatie = perms.get(codename="view_autorisatie", content_type=self.new_autorisatie_ct)
        delete_autorisatie = perms.get(codename="delete_autorisatie", content_type=self.new_autorisatie_ct)

        self.assertEqual(perms.contains(add_autorisatie), True)
        self.assertEqual(perms.contains(change_autorisatie), True)
        self.assertEqual(perms.contains(view_autorisatie), True)
        self.assertEqual(perms.contains(delete_autorisatie), True)
