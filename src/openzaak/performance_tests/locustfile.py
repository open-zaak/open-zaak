import random
from datetime import date
from itertools import count

from locust import HttpLocust, TaskSequence, TaskSet, seq_task, task

headers = {
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImNsaWVudF9pZGVudGlmaWVyIjoiZGVtbyJ9.eyJpc3MiOiJkZW1vIiwiaWF0IjoxNTY3NTEzOTQ3LCJjbGllbnRfaWQiOiJkZW1vIiwidXNlcl9pZCI6ImRlbW8iLCJ1c2VyX3JlcHJlc2VudGF0aW9uIjoiZGVtbyJ9.2muPkBfyKE4qlwhUFgbROQpZRrdMHMn97394Z6oj1_c",
    "Content-Type": "application/json",
}

zaak_headers = headers.copy()
zaak_headers.update({"Accept-Crs": "EPSG:4326", "Content-Crs": "EPSG:4326"})
ident_count = count(10000)


class FilloutTool(TaskSet):
    @task(20)
    def list_zaak(self):
        self.client.get("/zaken/api/v1/zaken", headers=zaak_headers)
        # TODO 3 requests


    @task(8)
    def get_zaak(self):
        self.client.get(
            "/zaken/api/v1/zaken/9f1d0635-54df-4974-bf58-3432dd0d776d",
            name='/zaken/api/v1/zaken/{uuid}',
            headers=zaak_headers,
        )

    @task(10)
    def create_zaak(self):
        today = date.today().strftime("%Y-%m-%d")
        body = {
            "zaaktype": "/catalogi/api/v1/zaaktypen/892ca451-c965-41f5-925a-5954e7c37156",
            "vertrouwelijkheidaanduiding": "openbaar",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "identificatie": f"ID_{next(ident_count)}",
            "registratiedatum": today,
            "startdatum": today,
            "toelichting": "test",
            "zaakgeometrie": f"POINT ({random.uniform(1, 100)} {random.uniform(1, 100)})",
        }
        self.client.post("/zaken/api/v1/zaken", json=body, headers=zaak_headers)

    @task(10)
    def zoek_zaak(self):
        body = {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [[
                            [4.932978, 52.370394],
                            [4.884489, 52.388366],
                            [4.881418, 52.363114],
                            [4.932978, 52.370394]
                        ]],
                    }
                }
            }

        self.client.post("/zaken/api/v1/zaken/_zoek", json=body, headers=zaak_headers)


class OpenzaakLocust(HttpLocust):
    # local
    host = "http://localhost:8000"
    task_set = FilloutTool
