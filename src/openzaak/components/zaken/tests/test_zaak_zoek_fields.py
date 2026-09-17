# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.api.scopes import SCOPE_CATALOGI_READ
from openzaak.components.catalogi.api.serializers import ZaakTypeSerializer
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_ALLES_LEZEN
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils.auth import JWTAuthMixin

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
from ..api.serializers import ZaakZoekSerializer
from ..api.serializers.zaken import ZoekFieldsSerializer
from .factories import (
    ResultaatFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS as POST_KWARGS, get_operation_url


class ZoekFieldsValidationTests(SimpleTestCase):
    def test_invalid_selections(self):
        for selection in (
            None,
            "uuid",
            {},
            [None],
            [True],
            [{}],
            ["unknown"],
            ["_expand"],
            [{"uuid": ["url"]}],
            [{"status": None}],
            [{"status": ["unknown"]}],
            [{"*": ["url"]}],
            {"fields": ["uuid"]},
        ):
            with self.subTest(selection=selection):
                serializer = ZaakZoekSerializer(data={"fields": selection})
                self.assertFalse(serializer.is_valid())
                self.assertIn("fields", serializer.errors)

    def test_camel_case_and_duplicate_nested_selections(self):
        serializer = ZaakZoekSerializer(
            data={
                "fields": [
                    "verantwoordelijkeOrganisatie",
                    {"status": ["datumStatusGezet"]},
                    {"status": ["statustoelichting"]},
                ]
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["fields"],
            {
                "verantwoordelijke_organisatie": None,
                "status": {"datum_status_gezet": None, "statustoelichting": None},
            },
        )


@temp_private_root()
class ZaakZoekFieldsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        cls.zaak = ZaakFactory.create()
        cls.url = get_operation_url("zaak__zoek")
        super().setUpTestData()

    def search(self, fields, *, query_params=None, **extra):
        return self.client.post(
            self.url,
            {"fields": fields, **extra},
            query_params=query_params,
            **POST_KWARGS,
        )

    def test_fields_are_parsed_once_per_request(self):
        with patch.object(
            ZoekFieldsSerializer,
            "to_internal_value",
            autospec=True,
            side_effect=ZoekFieldsSerializer.to_internal_value,
        ) as parse:
            response = self.search([{"zaaktype": ["identificatie"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(parse.call_count, 1)
        invalid_filter = self.search(["uuid"], uuid__in=["invalid"])
        self.assertEqual(invalid_filter.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shared_expansion_is_serialized_once_per_response(self):
        ZaakFactory.create_batch(3, zaaktype=self.zaak.zaaktype)
        with patch.object(
            ZaakTypeSerializer,
            "to_representation",
            autospec=True,
            side_effect=ZaakTypeSerializer.to_representation,
        ) as serialize:
            for _ in range(2):
                response = self.search([{"zaaktype": ["identificatie"]}])
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                results = response.json()["results"]
                self.assertEqual(len(results), 4)
                for result in results:
                    self.assertEqual(
                        result["_expand"]["zaaktype"],
                        {"identificatie": self.zaak.zaaktype.identificatie},
                    )
            self.assertEqual(serialize.call_count, 2)

    def test_only_selected_fields_and_pagination(self):
        ZaakFactory.create_batch(2)
        response = self.search(
            ["uuid", "verantwoordelijkeOrganisatie"], query_params={"pageSize": 2}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])
        self.assertEqual(len(data["results"]), 2)
        for result in data["results"]:
            self.assertEqual(set(result), {"uuid", "verantwoordelijkeOrganisatie"})

    def test_existing_filters_still_apply(self):
        ZaakFactory.create()
        response = self.search(["uuid"], uuid__in=[str(self.zaak.uuid)])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["results"], [{"uuid": str(self.zaak.uuid)}])

    def test_empty_results(self):
        response = self.search(["uuid"], uuid__in=[])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["results"], [])

    def test_empty_selection(self):
        response = self.search([])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["results"], [{}])

    def test_omitted_fields_and_wildcard_return_complete_response(self):
        complete = self.client.post(
            self.url, {"uuid__in": [str(self.zaak.uuid)]}, **POST_KWARGS
        )
        selected = self.search(["*"])

        self.assertEqual(complete.status_code, status.HTTP_200_OK, complete.data)
        self.assertEqual(selected.status_code, status.HTTP_200_OK, selected.data)
        self.assertEqual(selected.json(), complete.json())
        self.assertIn("omschrijving", complete.json()["results"][0])

    def test_nested_catalogus_selection(self):
        response = self.search(
            ["uuid", {"zaaktype": ["identificatie", {"catalogus": ["domein"]}]}]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        zaaktype = self.zaak.zaaktype
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "uuid": str(self.zaak.uuid),
                    "zaaktype": f"http://testserver{reverse(zaaktype)}",
                    "_expand": {
                        "zaaktype": {
                            "identificatie": zaaktype.identificatie,
                            "catalogus": f"http://testserver{reverse(zaaktype.catalogus)}",
                            "_expand": {
                                "catalogus": {"domein": zaaktype.catalogus.domein}
                            },
                        }
                    },
                }
            ],
        )

    def test_catalogus_expansion_is_prefetched(self):
        ZaakFactory.create_batch(3)

        with CaptureQueriesContext(connection) as queries:
            response = self.search([{"zaaktype": [{"catalogus": ["domein"]}]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.json()["results"]), 4)
        catalogus_queries = [
            query["sql"]
            for query in queries
            if 'FROM "catalogi_catalogus"' in query["sql"]
        ]
        self.assertEqual(len(catalogus_queries), 1, catalogus_queries)

    def test_nested_wildcard(self):
        zaak_status = StatusFactory.create(zaak=self.zaak)
        response = self.search([{"status": ["*"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.json()["results"][0]
        self.assertEqual(set(data), {"status", "_expand"})
        self.assertEqual(data["_expand"]["status"]["uuid"], str(zaak_status.uuid))
        self.assertIn("datumStatusGezet", data["_expand"]["status"])

    def test_null_relation(self):
        response = self.search([{"resultaat": ["*"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["results"], [{"resultaat": None}])

    def test_embedded_object(self):
        response = self.search([{"processobject": ["identificatie"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "processobject": {
                        "identificatie": self.zaak.processobject_identificatie
                    }
                }
            ],
        )

    def test_document_selection(self):
        document = EnkelvoudigInformatieObjectFactory.create(bestandsnaam="report.pdf")
        ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=document.canonical
        )
        EnkelvoudigInformatieObjectFactory.create(
            canonical=document.canonical,
            uuid=document.uuid,
            versie=2,
            identificatie=document.identificatie,
            bronorganisatie=document.bronorganisatie,
            informatieobjecttype=document.informatieobjecttype,
            bestandsnaam="report-v2.pdf",
        )
        response = self.search(
            [{"zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}]}]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        relation = response.json()["results"][0]["_expand"]["zaakinformatieobjecten"][0]
        self.assertEqual(set(relation), {"informatieobject", "_expand"})
        self.assertEqual(
            relation["_expand"], {"informatieobject": {"bestandsnaam": "report-v2.pdf"}}
        )

    def test_combined_nested_field_selection(self):
        StatusFactory.create(zaak=self.zaak)
        ResultaatFactory.create(zaak=self.zaak)
        document = EnkelvoudigInformatieObjectFactory.create(bestandsnaam="report.pdf")
        ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=document.canonical
        )
        fields = [
            "url",
            "uuid",
            "identificatie",
            "bronorganisatie",
            {
                "zaaktype": [
                    "identificatie",
                    "omschrijving",
                    {"catalogus": ["domein"]},
                ],
                "status": [{"statustype": ["volgnummer"]}, "datumStatusGezet"],
                "resultaat": ["*"],
                "zaakinformatieobjecten": [
                    {"informatieobject": ["inhoud", "bestandsnaam", "bestandsomvang"]}
                ],
                "processobject": ["identificatie"],
            },
        ]
        response = self.search(fields)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result = response.json()["results"][0]
        self.assertEqual(
            set(result),
            {
                "url",
                "uuid",
                "identificatie",
                "bronorganisatie",
                "zaaktype",
                "status",
                "resultaat",
                "zaakinformatieobjecten",
                "processobject",
                "_expand",
            },
        )
        self.assertEqual(result["uuid"], str(self.zaak.uuid))
        self.assertEqual(
            result["processobject"],
            {"identificatie": self.zaak.processobject_identificatie},
        )
        expanded = result["_expand"]
        self.assertEqual(
            set(expanded), {"zaaktype", "status", "resultaat", "zaakinformatieobjecten"}
        )
        self.assertEqual(
            set(expanded["zaaktype"]),
            {"identificatie", "omschrijving", "catalogus", "_expand"},
        )
        self.assertEqual(
            expanded["zaaktype"]["_expand"]["catalogus"],
            {"domein": self.zaak.zaaktype.catalogus.domein},
        )
        self.assertEqual(
            set(expanded["status"]), {"statustype", "datumStatusGezet", "_expand"}
        )
        self.assertEqual(
            set(expanded["status"]["_expand"]["statustype"]), {"volgnummer"}
        )
        relation = expanded["zaakinformatieobjecten"][0]
        self.assertEqual(set(relation), {"informatieobject", "_expand"})
        selected_document = relation["_expand"]["informatieobject"]
        self.assertEqual(
            set(selected_document), {"inhoud", "bestandsnaam", "bestandsomvang"}
        )
        self.assertEqual(selected_document["bestandsnaam"], "report.pdf")
        complete = self.client.post(self.url, {"expand": ["resultaat"]}, **POST_KWARGS)
        self.assertEqual(complete.status_code, status.HTTP_200_OK, complete.data)
        self.assertEqual(
            expanded["resultaat"], complete.json()["results"][0]["_expand"]["resultaat"]
        )

    def test_body_expansion_and_fields_are_mutually_exclusive(self):
        response = self.search([{"zaaktype": ["identificatie"]}], expand=["zaaktype"])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_fields_return_validation_response(self):
        response = self.search(["doesNotExist"])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalidParams", response.json())
        self.assertEqual(response.json()["invalidParams"][0]["name"], "fields")


class ZaakZoekFieldsAuthTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(
            zaaktype=cls.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        cls.url = get_operation_url("zaak__zoek")
        super().setUpTestData()

    def test_selection_does_not_bypass_zaak_authorizations(self):
        ZaakFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        response = self.client.post(self.url, {"fields": ["uuid"]}, **POST_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json()["results"], [{"uuid": str(self.zaak.uuid)}])

    def test_nested_selection_requires_component_read_scope(self):
        for fields, component, scope in (
            (
                [{"zaaktype": [{"catalogus": ["domein"]}]}],
                ComponentTypes.ztc,
                SCOPE_CATALOGI_READ,
            ),
            (
                [{"zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}]}],
                ComponentTypes.drc,
                SCOPE_DOCUMENTEN_ALLES_LEZEN,
            ),
        ):
            with self.subTest(component=component):
                data = {"fields": fields}
                response = self.client.post(self.url, data, **POST_KWARGS)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

                authorization = Autorisatie.objects.create(
                    applicatie=self.applicatie, component=component, scopes=[scope]
                )
                response = self.client.post(self.url, data, **POST_KWARGS)
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                authorization.delete()

    def test_plain_relation_url_does_not_require_expansion_scope(self):
        response = self.client.post(self.url, {"fields": ["zaaktype"]}, **POST_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.json()["results"],
            [{"zaaktype": f"http://testserver{reverse(self.zaaktype)}"}],
        )

    def test_selection_without_zaak_scope_is_forbidden(self):
        self.autorisatie.delete()
        response = self.client.post(self.url, {"fields": []}, **POST_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_omitted_expanded_field_does_not_bypass_permissions(self):
        response = self.client.post(
            self.url,
            {"fields": ["uuid"]},
            query_params={"expand": "zaaktype"},
            **POST_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
