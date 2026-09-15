# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from privates.test import temp_private_root
from rest_framework import serializers, status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.api.scopes import SCOPE_CATALOGI_READ
from openzaak.components.catalogi.api.serializers import ZaakTypeSerializer
from openzaak.components.catalogi.tests.factories import (
    CheckListItemFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_ALLES_LEZEN
from openzaak.components.documenten.tests.factories import (
    BestandsDeelFactory,
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils.auth import JWTAuthMixin
from openzaak.utils.expansion import SelectedFieldsExpansion

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
from ..api.serializers import ZaakSerializer, ZaakZoekSerializer
from ..api.serializers.zaken import ZaakZoekFieldsSerializer, ZoekFieldsSerializer
from ..api.viewsets import ZaakViewSet
from .factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS as POST_KWARGS, get_operation_url


class ZoekFieldsValidationTests(SimpleTestCase):
    def test_response_serializer_is_required(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "ZoekFieldsSerializer requires parent_serializer_class.",
        ):
            ZoekFieldsSerializer().run_validation(["uuid"])

    def test_write_only_fields_cannot_be_selected(self):
        class ResponseSerializer(serializers.Serializer):
            secret = serializers.CharField(write_only=True)

        class SearchFields(ZoekFieldsSerializer):
            parent_serializer_class = ResponseSerializer

        with self.assertRaises(serializers.ValidationError) as error:
            SearchFields().run_validation(["secret"])

        self.assertEqual(error.exception.detail[0].code, "unknown_field")

    def test_duplicate_selections_preserve_nested_fields(self):
        for entries in (
            [{"status": [{"statustype": ["volgnummer"]}]}, {"status": ["statustype"]}],
            [{"status": ["statustype"]}, {"status": [{"statustype": ["volgnummer"]}]}],
            [{"status": [{"statustype": ["volgnummer"]}]}, "status"],
        ):
            with self.subTest(entries=entries):
                serializer = ZaakZoekSerializer(data={"fields": entries})
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(
                    serializer.validated_data["fields"],
                    {"status": {"statustype": {"volgnummer": None}}},
                )

    def test_selected_inclusions_are_cached_per_view(self):
        request = SimpleNamespace(method="POST", data={"fields": []}, query_params={})
        for selection, expected in (
            (
                {"zaaktype": {"catalogus": {"domein": None}}},
                "zaaktype,zaaktype.catalogus",
            ),
            ({"status": None}, ""),
        ):
            with self.subTest(selection=selection):
                view = ZaakViewSet()
                view.action = "_zoek"
                view._selected_fields = selection
                self.assertIsNone(view._selected_inclusions)
                with patch.object(
                    view, "get_serializer_class", wraps=view.get_serializer_class
                ) as get_serializer_class:
                    self.assertEqual(view.get_requested_inclusions(request), expected)
                    self.assertEqual(view.get_requested_inclusions(request), expected)
                    get_serializer_class.assert_called_once()
                    # Explicit expand parameters are still read on each call.
                    request.query_params["expand"] = "resultaat"
                    self.assertEqual(
                        view.get_requested_inclusions(request),
                        ",".join(filter(None, ["resultaat", expected])),
                    )
                    get_serializer_class.assert_called_once()
                request.query_params.clear()

    def test_prefetch_planning_reuses_serializers_only_within_one_call(self):
        selection = {
            "zaaktype": {"identificatie": None},
            "hoofdzaak": {"zaaktype": {"omschrijving": None}},
        }
        with patch.object(
            ZaakTypeSerializer,
            "get_fields",
            autospec=True,
            side_effect=ZaakTypeSerializer.get_fields,
        ) as get_fields:
            for expected_calls in (1, 2):
                prefetches = SelectedFieldsExpansion.selected_prefetches(
                    ZaakSerializer(), selection
                )
                self.assertEqual(get_fields.call_count, expected_calls)
                self.assertEqual(
                    set(prefetches), {"_zaaktype", "hoofdzaak", "hoofdzaak___zaaktype"}
                )

    def test_field_selection_uses_configured_response_serializer(self):
        class ResponseSerializer(serializers.Serializer):
            display_name = serializers.CharField()
            inclusion_serializers = {}

        class SearchFields(ZoekFieldsSerializer):
            parent_serializer_class = ResponseSerializer

        class SearchSerializer(serializers.Serializer):
            fields = SearchFields()

        serializer = SearchSerializer(data={"fields": ["displayName"]})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["fields"], {"display_name": None})

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

    def test_unknown_nested_field_uses_api_casing(self):
        serializer = ZaakZoekSerializer(
            data={"fields": [{"status": ["datum_status_onbekend"]}]}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("status.datumStatusOnbekend", str(serializer.errors["fields"]))


@temp_private_root()
class ZaakZoekFieldsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

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
            ZaakZoekFieldsSerializer,
            "to_internal_value",
            autospec=True,
            side_effect=ZaakZoekFieldsSerializer.to_internal_value,
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
        zaken = ZaakFactory.create_batch(2)
        response = self.search(
            ["uuid", "verantwoordelijkeOrganisatie"], query_params={"pageSize": 2}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        host_prefix = response.wsgi_request.build_absolute_uri("/").rstrip("/")
        data = response.json()
        self.assertEqual(
            data,
            {
                "count": 3,
                "next": f"{host_prefix}{self.url}?page=2&pageSize=2",
                "previous": None,
                "results": [
                    {
                        "uuid": str(zaak.uuid),
                        "verantwoordelijkeOrganisatie": zaak.verantwoordelijke_organisatie,
                    }
                    for zaak in reversed(zaken)
                ],
            },
        )

    def test_selected_fields_without_pagination(self):
        with patch.object(ZaakViewSet, "pagination_class", None):
            response = self.search(["uuid"])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.json(), [{"uuid": str(self.zaak.uuid)}])

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
        host_prefix = response.wsgi_request.build_absolute_uri("/").rstrip("/")
        zaaktype = self.zaak.zaaktype
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "uuid": str(self.zaak.uuid),
                    "zaaktype": f"{host_prefix}{reverse(zaaktype)}",
                    "_expand": {
                        "zaaktype": {
                            "identificatie": zaaktype.identificatie,
                            "catalogus": f"{host_prefix}{reverse(zaaktype.catalogus)}",
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

    def test_relation_urls_do_not_query_once_per_zaak(self):
        zaken = ZaakFactory.create_batch(3)
        for zaak in (self.zaak, *zaken):
            StatusFactory.create(zaak=zaak)
        for fields, table in (
            ([{"zaaktype": ["url"]}], '"catalogi_zaaktype"'),
            ([{"status": ["url"]}], '"zaken_status"'),
        ):
            with CaptureQueriesContext(connection) as single_queries:
                single_response = self.search(fields, uuid__in=[str(self.zaak.uuid)])
            with (
                self.subTest(fields=fields),
                CaptureQueriesContext(connection) as queries,
            ):
                response = self.search(fields)
            self.assertEqual(single_response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertLessEqual(len(queries) - len(single_queries), 2)
            relation_queries = [
                q["sql"] for q in queries if f"FROM {table}" in q["sql"]
            ]
            # Multiple expansion paths can prefetch the same table, but their
            # query count must remain independent of the number of zaken.
            single_relation_queries = [
                q for q in single_queries if f"FROM {table}" in q["sql"]
            ]
            self.assertEqual(
                len(relation_queries), len(single_relation_queries), relation_queries
            )

    def test_status_and_hoofdzaak_expansions_have_constant_query_count(self):
        zaken = [ZaakFactory.create(hoofdzaak=ZaakFactory.create()) for _ in range(3)]
        for zaak in zaken:
            for instance in (zaak, zaak.hoofdzaak):
                zaak_status = StatusFactory.create(
                    zaak=instance,
                    statustype__zaaktype=instance.zaaktype,
                    gezetdoor=RolFactory.create(zaak=instance),
                )
                CheckListItemFactory.create(statustype=zaak_status.statustype)
                ZaakInformatieObjectFactory.create(zaak=instance, status=zaak_status)

        fields = [
            "uuid",
            {
                "hoofdzaak": [
                    "*",
                    {"zaaktype": ["identificatie", "omschrijving"]},
                    {"status": ["*", {"statustype": ["*"]}]},
                ],
                "zaaktype": ["identificatie", {"catalogus": ["domein"]}],
                "status": ["*", {"statustype": ["volgnummer"]}],
                "eigenschappen": ["*"],
                "resultaat": ["*"],
            },
        ]
        with CaptureQueriesContext(connection) as single_queries:
            single_response = self.search(fields, uuid__in=[str(zaken[0].uuid)])
        with CaptureQueriesContext(connection) as multiple_queries:
            response = self.search(fields, uuid__in=[str(zaak.uuid) for zaak in zaken])

        self.assertEqual(single_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.json()["results"]), 3)
        self.assertEqual(len(multiple_queries), len(single_queries))
        for result in response.json()["results"]:
            expanded_status = result["_expand"]["hoofdzaak"]["_expand"]["status"]
            self.assertTrue(expanded_status["indicatieLaatstGezetteStatus"])
            self.assertTrue(expanded_status["_expand"]["statustype"]["isEindstatus"])
            self.assertEqual(len(expanded_status["zaakinformatieobjecten"]), 1)
            self.assertEqual(
                len(
                    expanded_status["_expand"]["statustype"]["checklistitemStatustype"]
                ),
                1,
            )

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

    def test_legacy_expansion_has_constant_query_count(self):
        zaken = ZaakFactory.create_batch(3)
        for zaak in zaken:
            zaak_status = StatusFactory.create(
                zaak=zaak,
                statustype__zaaktype=zaak.zaaktype,
                gezetdoor=RolFactory.create(zaak=zaak),
            )
            CheckListItemFactory.create(statustype=zaak_status.statustype)
            ZaakInformatieObjectFactory.create(zaak=zaak, status=zaak_status)

        for in_query in (False, True):
            with self.subTest(in_query=in_query):
                data = (
                    {}
                    if in_query
                    else {"expand": ["zaaktype", "status", "status.statustype"]}
                )
                params = (
                    {"expand": "zaaktype,status,status.statustype"} if in_query else {}
                )
                with CaptureQueriesContext(connection) as single_queries:
                    single = self.client.post(
                        self.url,
                        {**data, "uuid__in": [str(zaken[0].uuid)]},
                        query_params=params,
                        **POST_KWARGS,
                    )
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.post(
                        self.url,
                        {**data, "uuid__in": [str(zaak.uuid) for zaak in zaken]},
                        query_params=params,
                        **POST_KWARGS,
                    )
                self.assertEqual(single.status_code, status.HTTP_200_OK, single.data)
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                self.assertEqual(len(queries), len(single_queries))
                self.assertEqual(len(response.json()["results"]), 3)
                for result in response.json()["results"]:
                    self.assertIn("bronorganisatie", result)
                    self.assertIn("beginObject", result["_expand"]["zaaktype"])
                    expanded_status = result["_expand"]["status"]
                    self.assertTrue(expanded_status["indicatieLaatstGezetteStatus"])
                    self.assertEqual(len(expanded_status["zaakinformatieobjecten"]), 1)
                    self.assertTrue(
                        expanded_status["_expand"]["statustype"]["isEindstatus"]
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

    def test_scalar_fields_do_not_prefetch_relations(self):
        StatusFactory.create(zaak=self.zaak)
        ZaakInformatieObjectFactory.create(zaak=self.zaak)
        with CaptureQueriesContext(connection) as queries:
            response = self.search(["uuid", "identificatie"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for table in (
            "zaken_status",
            "zaken_zaakinformatieobject",
            "catalogi_zaaktype",
            "zaken_rol",
            "zaken_zaakeigenschap",
            "documenten_enkelvoudiginformatieobject",
        ):
            self.assertFalse(any(f'FROM "{table}"' in q["sql"] for q in queries), table)

    def test_document_fields_do_not_fetch_unselected_relations(self):
        document = EnkelvoudigInformatieObjectFactory.create()
        ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=document.canonical
        )
        with CaptureQueriesContext(connection) as queries:
            response = self.search(
                [{"zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}]}]
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for table in ("documenten_bestandsdeel", "catalogi_informatieobjecttype"):
            self.assertFalse(any(f'FROM "{table}"' in q["sql"] for q in queries), table)

    def test_shared_expansion_with_different_field_selections(self):
        self.zaak.hoofdzaak = ZaakFactory.create(zaaktype=self.zaak.zaaktype)
        self.zaak.save()
        response = self.search(
            [
                {"zaaktype": ["identificatie"]},
                {"hoofdzaak": [{"zaaktype": ["omschrijving"]}]},
            ],
            uuid__in=[str(self.zaak.uuid)],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expanded = response.json()["results"][0]["_expand"]
        self.assertEqual(set(expanded["zaaktype"]), {"identificatie"})
        self.assertEqual(
            set(expanded["hoofdzaak"]["_expand"]["zaaktype"]), {"omschrijving"}
        )

    def test_document_wildcard_prefetches_file_parts_and_locks(self):
        zaken = ZaakFactory.create_batch(3)
        for zaak in zaken:
            document = EnkelvoudigInformatieObjectFactory.create(canonical__lock="lock")
            BestandsDeelFactory.create(
                informatieobject=document.canonical, volgnummer=1
            )
            ZaakInformatieObjectFactory.create(
                zaak=zaak, informatieobject=document.canonical
            )
        fields = [{"zaakinformatieobjecten": [{"informatieobject": ["*"]}]}]
        with CaptureQueriesContext(connection) as single_queries:
            single = self.search(fields, uuid__in=[str(zaken[0].uuid)])
        with CaptureQueriesContext(connection) as queries:
            response = self.search(fields, uuid__in=[str(zaak.uuid) for zaak in zaken])
        self.assertEqual(single.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(queries), len(single_queries))
        for result in response.json()["results"]:
            document = result["_expand"]["zaakinformatieobjecten"][0]["_expand"][
                "informatieobject"
            ]
            self.assertTrue(document["locked"])
            self.assertEqual(len(document["bestandsdelen"]), 1)
            self.assertEqual(document["bestandsdelen"][0]["lock"], "lock")

    def test_document_expansion_has_constant_query_count(self):
        zaken = ZaakFactory.create_batch(3)
        for zaak in zaken:
            for _ in range(2):
                document = EnkelvoudigInformatieObjectFactory.create(
                    bestandsnaam="report.pdf"
                )
                BestandsDeelFactory.create(
                    informatieobject=document.canonical, volgnummer=1
                )
                ZaakInformatieObjectFactory.create(
                    zaak=zaak, informatieobject=document.canonical
                )

        fields = [
            "uuid",
            {
                "zaakinformatieobjecten": [
                    {"informatieobject": ["inhoud", "bestandsnaam", "bestandsomvang"]}
                ]
            },
        ]
        with CaptureQueriesContext(connection) as single_queries:
            single_response = self.search(fields, uuid__in=[str(zaken[0].uuid)])
        with CaptureQueriesContext(connection) as multiple_queries:
            response = self.search(fields, uuid__in=[str(zaak.uuid) for zaak in zaken])

        self.assertEqual(single_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.json()["results"]), 3)
        self.assertEqual(len(multiple_queries), len(single_queries))
        for result in response.json()["results"]:
            documents = result["_expand"]["zaakinformatieobjecten"]
            self.assertEqual(len(documents), 2)
            for document in documents:
                expanded = document["_expand"]["informatieobject"]
                self.assertEqual(
                    set(expanded), {"inhoud", "bestandsnaam", "bestandsomvang"}
                )
                self.assertEqual(expanded["bestandsnaam"], "report.pdf")
                self.assertEqual(expanded["bestandsomvang"], len(b"some data"))
                self.assertTrue(expanded["inhoud"])

    def test_combined_nested_field_selection(self):
        zaak_status = StatusFactory.create(zaak=self.zaak)
        resultaat = ResultaatFactory.create(zaak=self.zaak)
        document = EnkelvoudigInformatieObjectFactory.create(bestandsnaam="report.pdf")
        relation = ZaakInformatieObjectFactory.create(
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
                "status": ["uuid", {"statustype": ["volgnummer"]}],
                "resultaat": ["uuid"],
                "zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}],
                "processobject": ["identificatie"],
            },
        ]
        response = self.search(fields)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        host_prefix = response.wsgi_request.build_absolute_uri("/").rstrip("/")
        zaaktype = self.zaak.zaaktype

        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "url": f"{host_prefix}{reverse(self.zaak)}",
                        "uuid": str(self.zaak.uuid),
                        "identificatie": self.zaak.identificatie,
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "zaaktype": f"{host_prefix}{reverse(zaaktype)}",
                        "status": f"{host_prefix}{reverse(zaak_status)}",
                        "resultaat": f"{host_prefix}{reverse(resultaat)}",
                        "zaakinformatieobjecten": [f"{host_prefix}{reverse(relation)}"],
                        "processobject": {
                            "identificatie": self.zaak.processobject_identificatie
                        },
                        "_expand": {
                            "zaaktype": {
                                "identificatie": zaaktype.identificatie,
                                "omschrijving": zaaktype.zaaktype_omschrijving,
                                "catalogus": f"{host_prefix}{reverse(zaaktype.catalogus)}",
                                "_expand": {
                                    "catalogus": {"domein": zaaktype.catalogus.domein}
                                },
                            },
                            "status": {
                                "uuid": str(zaak_status.uuid),
                                "statustype": f"{host_prefix}{reverse(zaak_status.statustype)}",
                                "_expand": {
                                    "statustype": {
                                        "volgnummer": zaak_status.statustype.statustypevolgnummer
                                    }
                                },
                            },
                            "resultaat": {"uuid": str(resultaat.uuid)},
                            "zaakinformatieobjecten": [
                                {
                                    "informatieobject": f"{host_prefix}{reverse(document)}",
                                    "_expand": {
                                        "informatieobject": {
                                            "bestandsnaam": "report.pdf"
                                        }
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        )

    def test_body_expansion_and_fields_are_mutually_exclusive(self):
        response = self.search([{"zaaktype": ["identificatie"]}], expand=["zaaktype"])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            get_validation_errors(response, "nonFieldErrors")["code"], "invalid_field"
        )

    def test_query_expansion_and_fields_are_mutually_exclusive(self):
        for expand in ("zaaktype", ""):
            with self.subTest(expand=expand):
                response = self.search(["uuid"], query_params={"expand": expand})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    get_validation_errors(response, "nonFieldErrors")["code"],
                    "invalid_field",
                )

    def test_invalid_fields_return_validation_response(self):
        response = self.search(["doesNotExist"])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            get_validation_errors(response, "fields")["code"], "unknown_field"
        )


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
        host_prefix = response.wsgi_request.build_absolute_uri("/").rstrip("/")
        self.assertEqual(
            response.json()["results"],
            [{"zaaktype": f"{host_prefix}{reverse(self.zaaktype)}"}],
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
