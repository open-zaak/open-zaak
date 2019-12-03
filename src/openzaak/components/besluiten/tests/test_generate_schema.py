from io import StringIO

from django.core.management import call_command
from django.test import override_settings

from rest_framework.test import APITestCase


class CreateNotifKanaalTestCase(APITestCase):
    def test_kanaal_create_with_name(self):
        stdout = StringIO()
        call_command(
            "generate_swagger_component",
            "swagger2.0.json",
            overwrite=True,
            format="json",
            mock_request=True,
            url="https://example.com/api/v1",
            component="besluiten",
            stdout=stdout,
        )
