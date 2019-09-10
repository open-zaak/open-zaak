import uuid
from base64 import b64encode
import random
from datetime import date, datetime
from itertools import count

from locust import HttpLocust, TaskSet, task

headers = {
    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImNsaWVudF9pZGVudGlmaWVyIjoiZGVtbyJ9.eyJpc3MiOiJkZW1vIiwiaWF0IjoxNTY3NTEzOTQ3LCJjbGllbnRfaWQiOiJkZW1vIiwidXNlcl9pZCI6ImRlbW8iLCJ1c2VyX3JlcHJlc2VudGF0aW9uIjoiZGVtbyJ9.2muPkBfyKE4qlwhUFgbROQpZRrdMHMn97394Z6oj1_c",
    "Content-Type": "application/json",
}

zaak_headers = headers.copy()
zaak_headers.update({"Accept-Crs": "EPSG:4326", "Content-Crs": "EPSG:4326"})


class FilloutTool(TaskSet):
    @task(20)
    def zaken_overzicht(self):
        self.client.get("/zaken/api/v1/zaken", headers=zaak_headers)
        self.client.get("/zaken/api/v1/statussen", headers=headers)
        self.client.get("/catalogi/api/v1/zaaktypen", headers=headers)
        self.client.get("/catalogi/api/v1/statustypen", headers=headers)

    @task(10)
    def zaak_zoeken_op_locatie(self):
        body = {
            "zaakgeometrie": {
                "within": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [4.932978, 52.370394],
                            [4.884489, 52.388366],
                            [4.881418, 52.363114],
                            [4.932978, 52.370394],
                        ]
                    ],
                }
            }
        }

        self.client.post("/zaken/api/v1/zaken/_zoek", json=body, headers=zaak_headers)

    def zaak_zoeken_op_persoon(self):
        # FIXME how to search by person?
        pass

    @task(8)
    def zaak_details(self):
        # Zaken API
        self.client.get(
            "/zaken/api/v1/zaken/c4b337dc-c540-4275-b15a-82beaff24a1e",
            name="/zaken/api/v1/zaken/{uuid}",
            headers=zaak_headers,
        )
        self.client.get(
            "/zaken/api/v1/statussen/295a50a4-5d8e-489c-a61d-fbcb539e6f2c",
            params={'zaak': "/zaken/api/v1/zaken/c4b337dc-c540-4275-b15a-82beaff24a1e"},
            name="/zaken/api/v1/statussen/{uuid}",
            headers=headers
        )
        self.client.get(
            "/zaken/api/v1/resultaten/30918c7c-ae87-4111-9ca0-cd3fcb45b712",
            name="/zaken/api/v1/resultaten/{uuid}",
            headers=headers
        )
        self.client.get(
            "/zaken/api/v1/rollen",
            params={'zaak': "/zaken/api/v1/zaken/c4b337dc-c540-4275-b15a-82beaff24a1e"},
            name="/zaken/api/v1/rollen",
            headers=headers
        )
        # * 1x ZAAKOBJECTen (`GET /api/v1/zaakobjecten?zaak=/api/v1/zaken/d4d..2e8`)

        # Catalogi API
        self.client.get(
            "/catalogi/api/v1/zaaktypen/892ca451-c965-41f5-925a-5954e7c37156",
            name="/catalogi/api/v1/zaaktypen/{uuid}",
            headers=headers
        )
        self.client.get(
            "/catalogi/api/v1/statustypen/cd70ba43-0eb3-4e93-90c6-e70fb67dcf61",
            name="/catalogi/api/v1/statustypen/{uuid}",
            headers=headers
        )
        self.client.get(
            "/catalogi/api/v1/besluittype/ca3187b4-d6eb-476c-b27b-fa4efa6ec020",
            name="/catalogi/api/v1/besluittypen/{uuid}",
            headers=headers
        )
        self.client.get(
            "/catalogi/api/v1/resultaattypen/6c375048-951f-44e1-968c-49389376813a",
            name="/catalogi/api/v1/resultaattypen/{uuid}",
            headers=headers
        )

        # Documenten API
        # TODO
        # * 1x OBJECTINFORMATIEOBJECTen opvragen (`GET /api/v1/objectinformatieobjecten?object=/api/v1/zaken/d4d..2e8`)

        for uuid in ['d13123b6-81c9-4bbe-a6f5-359a9aacc8bf',
                     'c42c7b2e-f155-410e-8485-69ba18252df4',
                     'a08673f8-bedd-42e2-9de5-9ed0ee1d9b5c']:
            self.client.get(
                f"/documenten/api/v1/enkelvoudiginformatieobjecten/{uuid}",
                name="/documenten/api/v1/enkelvoudiginformatieobjecten/{uuid}",
                headers=headers
            )

        # Besluiten API
        self.client.get(
            "/zaken/api/v1/rollen",
            params={'zaak': "/zaken/api/v1/zaken/c4b337dc-c540-4275-b15a-82beaff24a1e"},
            name="/zaken/api/v1/rollen",
            headers=headers
        )

    def geschiedenis(self):
        # TODO
        # Zaken API
        # * 1x AUDITTRAIL (`GET /api/v1/zaken/d4d..2e8/audittrail`)

        # Documenten API
        # * 3x AUDITTRAIL (`GET /api/v1/enkelvoudiginformatieobjecten/cd6..d90/audittrail`)
        #
        # Besluiten API
        # * 1x AUDITTRAIL (`GET /api/v1/besluiten/a28..6d3/audittrail`)
        pass

    # @task(10)
    def zaak_aanmaken(self):
        today = date.today().strftime("%Y-%m-%d")
        body = {
            "zaaktype": "/catalogi/api/v1/zaaktypen/892ca451-c965-41f5-925a-5954e7c37156",
            "vertrouwelijkheidaanduiding": "openbaar",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "identificatie": f"ID_{uuid.uuid4()}",
            "registratiedatum": today,
            "startdatum": today,
            "toelichting": "test",
            "zaakgeometrie": f"POINT ({random.uniform(1, 50)} {random.uniform(50, 100)})",
        }
        self.client.post("/zaken/api/v1/zaken", json=body, headers=zaak_headers)

    # @task(20)
    def status_toevoegen(self):
        today = datetime.today().isoformat()
        body = {
            "zaak": "/zaken/api/v1/zaken/42498a55-43f4-4d5c-b386-1db91c0ef3a9",
            "statustype": "/catalogi/api/v1/statustypen/cd70ba43-0eb3-4e93-90c6-e70fb67dcf61",
            "datumStatusGezet": today,
        }
        self.client.post("/zaken/api/v1/statussen", json=body, headers=headers)

    def betrokkene_toevoegen(self):
        # TODO - fat rollen
        pass

    def document_toevoegen(self):
        body = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": "/catalogi/api/v1/informatieobjecttypen/95666244-aa4e-4848-9643-377670bd8cf1",
            "vertrouwelijkheidaanduiding": "openbaar",
        }
        self.client.post("/documenten/api/v1/enkelvoudiginformatieobjecten", json=body, headers=headers)

    def besluit_toevoegen(self):
        # TODO
        pass

    def resultaat_toevoegen(self):
        zaak_body = {
            "zaaktype": "/catalogi/api/v1/zaaktypen/892ca451-c965-41f5-925a-5954e7c37156",
            "vertrouwelijkheidaanduiding": "openbaar",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "identificatie": f"ID_{uuid.uuid4()}",
            "registratiedatum": date.today().strftime("%Y-%m-%d"),
            "startdatum": date.today().strftime("%Y-%m-%d"),
            "toelichting": "test",
            "zaakgeometrie": f"POINT ({random.uniform(1, 50)} {random.uniform(50, 100)})",
        }
        zaak_response = self.client.post("/zaken/api/v1/zaken", json=zaak_body, headers=zaak_headers)
        zaak_url = zaak_response.json()['url']

        resultaat_body = {
            "zaaktype": zaak_url,
            "omschrijving": "illum",
            "resultaattypeomschrijving": 'https://referentielijsten-api.vng.cloud/api/v1/resultaattypeomschrijvingen/e6a0c939-3404-45b0-88e3-76c94fb80ea7',
            # "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": 'afgehandeld',
                "einddatumBekend": False,
                "procestermijn": "P10Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }
        self.client.post("/zaken/api/v1/resultaten", json=resultaat_body, headers=headers)


class OpenzaakLocust(HttpLocust):
    # local
    host = "http://localhost:8000"
    task_set = FilloutTool
