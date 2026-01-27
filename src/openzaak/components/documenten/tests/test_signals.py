from django.test import TestCase

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)


class TestEnkelvoudigInformatieObjectSignals(TestCase):
    def test_saving_eio_sets_canonical_latest_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )

        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio1)

        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio2)

    def test_deleting_eio_resets_canonical_latest_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical)
        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical)

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio2)

        eio2.delete()

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, eio1)

        eio1.delete()

        canonical.refresh_from_db()
        self.assertEqual(canonical.latest_version, None)
