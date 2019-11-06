from django.test import TestCase

from ..factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)


class LastVersionTests(TestCase):
    def test_canonical_last_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory()
        eio1 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)
        eio2 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)
        eio3 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=3)

        self.assertEqual(canonical.latest_version, eio3)
