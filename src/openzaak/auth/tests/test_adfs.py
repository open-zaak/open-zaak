from django.core.cache import cache
from django.test import TestCase

from ..adfs import Settings
from ..models import ADFSConfig


class ADFSConfigTests(TestCase):
    def setUp(self):
        self.addCleanup(cache.clear)

    def test_default_on_premise(self):
        config = ADFSConfig.get_solo()

        # set the required fields
        config.server = "adfs.gemeente.nl"
        config.client_id = "ad8b1284-7394-4e3b-8495-48dc62419260"
        config.relying_party_id = "ad8b1284-7394-4e3b-8495-48dc62419260"
        config.save()

        expected = {
            "SERVER": "adfs.gemeente.nl",
            "TENANT_ID": "adfs",
            "CLIENT_ID": "ad8b1284-7394-4e3b-8495-48dc62419260",
            "RELYING_PARTY_ID": "ad8b1284-7394-4e3b-8495-48dc62419260",
            "AUDIENCE": "microsoft:identityserver:ad8b1284-7394-4e3b-8495-48dc62419260",
            "CA_BUNDLE": True,
            "CLAIM_MAPPING": {
                "first_name": "given_name",
                "last_name": "family_name",
                "email": "email",
            },
            "USERNAME_CLAIM": "winaccountname",
            "GROUPS_CLAIM": "group",
        }

        self.assertEqual(config.as_settings(), expected)

    def test_default_azure(self):
        config = ADFSConfig.get_solo()

        # set the required fields
        config.tenant_id = "1234"
        config.client_id = "59c20eb9-57d9-4ec9-b88a-96b0c49ec238"
        config.relying_party_id = "https://sergeimaykinmedia.onmicrosoft.com/8595dca3-85f5-4104-98f5-bddec3970a22"
        config.save()

        expected = {
            "TENANT_ID": "1234",
            "CLIENT_ID": "59c20eb9-57d9-4ec9-b88a-96b0c49ec238",
            "RELYING_PARTY_ID": "https://sergeimaykinmedia.onmicrosoft.com/8595dca3-85f5-4104-98f5-bddec3970a22",
            "AUDIENCE": "https://sergeimaykinmedia.onmicrosoft.com/8595dca3-85f5-4104-98f5-bddec3970a22",
            "CA_BUNDLE": True,
            "CLAIM_MAPPING": {
                "first_name": "given_name",
                "last_name": "family_name",
                "email": "email",
            },
            "USERNAME_CLAIM": "upn",
            "GROUPS_CLAIM": "group",
        }

        self.assertEqual(config.as_settings(), expected)

    def test_custom_settings(self):
        config = ADFSConfig.get_solo()
        config.server = "adfs.gemeente.nl"
        config.save()

        settings = Settings()

        self.assertEqual(settings.SERVER, "adfs.gemeente.nl")

        config.server = "adfs2.gemeente.nl"
        config.save()
        self.assertEqual(settings.SERVER, "adfs2.gemeente.nl")
