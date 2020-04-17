from django.test import TestCase


class FrontPageTests(TestCase):
    def test_front_page_available(self):
        response = self.client.get("")

        self.assertEqual(response.status_code, 200)
