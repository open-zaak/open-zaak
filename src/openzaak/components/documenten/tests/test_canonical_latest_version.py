# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.test import TestCase

from openzaak.components.documenten.tasks import set_canonical_latest_version
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests.structlog import capture_logs


class TestEnkelvoudigInformatieObjectSignals(TestCase):
    def test_saving_eio_sets_canonical_latest_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )

        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio1)

        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio2)

    def test_deleting_eio_resets_canonical_latest_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)
        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio2)

        eio2.delete()

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio1)

        eio1.delete()

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, None)

    def test_on_update(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)
        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)

        canonical.refresh_from_db()
        self.assertEqual(canonical.enkelvoudiginformatieobject_set.first(), eio2)
        self.assertEqual(canonical.latest_version, eio2)

        eio1.save()

        canonical.refresh_from_db()
        self.assertEqual(canonical.enkelvoudiginformatieobject_set.first(), eio2)
        self.assertEqual(canonical.latest_version, eio2)


class TestTask(TestCase):
    def test_task_updates_outdated_canonicals(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)
        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)
        canonical.latest_version = None
        canonical.save()

        with capture_logs() as cap_logs:
            set_canonical_latest_version.run()

        log = next(
            log
            for log in cap_logs
            if log["event"] == "outdated_canonical_latest_versions"
        )
        self.assertEqual(log["count"], 1)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio2)
