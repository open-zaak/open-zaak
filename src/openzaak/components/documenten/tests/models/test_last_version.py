from django.test import TestCase, override_settings

from ..factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)


@override_settings(CMIS_ENABLED=False)
class LastVersionTests(TestCase):
    def test_canonical_last_version(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory()
        EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=1)
        EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=2)
        eio3 = EnkelvoudigInformatieObjectFactory.create(canonical=canonical, versie=3)

        self.assertEqual(canonical.latest_version, eio3)
