from rest_framework.test import APITestCase


class BatchRequestTests(APITestCase):
    def test_batch_get(self):
        request_body = [
            {"method": "get", "url": "/besluiten/api/v1/",},
            {"method": "get", "url": "/autorisaties/api/v1/",},
        ]

        response = self.client.post("/api/v1/batch", request_body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "status": 200,
                    "body": {
                        "besluiten": "http://testserver/besluiten/api/v1/besluiten",
                        "besluitinformatieobjecten": "http://testserver/besluiten/api/v1/besluitinformatieobjecten",
                    },
                },
                {
                    "status": 200,
                    "body": {
                        "applicaties": "http://localhost:8000/autorisaties/api/v1/applicaties"
                    },
                },
            ],
        )
