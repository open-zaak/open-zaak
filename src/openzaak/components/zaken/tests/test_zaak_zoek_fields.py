# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import SimpleTestCase, tag
from django.test.utils import CaptureQueriesContext

from privates.test import temp_private_root
from rest_framework import serializers, status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors

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


@tag("gh-2539")
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
                self.assertTrue(serializer.is_valid())
                self.assertEqual(
                    serializer.validated_data["fields"],
                    {"status": {"statustype": {"volgnummer": None}}},
                )

    def test_repeated_nested_selections_merge_all_fields(self):
        serializer = ZaakZoekSerializer(
            data={
                "fields": [
                    {"status": [{"statustype": ["volgnummer"]}]},
                    {"status": [{"statustype": ["omschrijving"]}]},
                ]
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["fields"],
            {"status": {"statustype": {"volgnummer": None, "omschrijving": None}}},
        )

    def test_nested_serializer_selection(self):
        class FieldSerializer(serializers.Serializer):
            display_name = serializers.CharField()

        class ResponseSerializer(serializers.Serializer):
            nested_field = FieldSerializer()

        class SearchFields(ZoekFieldsSerializer):
            parent_serializer_class = ResponseSerializer

        self.assertEqual(
            SearchFields().run_validation([{"nestedField": ["displayName"]}]),
            {"nested_field": {"display_name": None}},
        )

    def test_inclusion_viewset_without_lookup_alias(self):
        view = ZaakViewSet()
        view.action = "_zoek"
        view.format_kwarg = None
        view.request = SimpleNamespace(
            method="POST", data={"expand": ["_zaaktype"]}, query_params={}
        )
        view.inclusion_viewsets = {
            "_zaaktype": "openzaak.components.catalogi.api.viewsets.ZaakTypeViewSet"
        }

        queryset = view.get_queryset()
        prefetch = next(
            prefetch
            for prefetch in queryset._prefetch_related_lookups
            if getattr(prefetch, "prefetch_through", None) == "_zaaktype"
        )
        self.assertIs(prefetch.queryset.model, ZaakTypeFactory._meta.model)
        self.assertIn("catalogus", prefetch.queryset.query.select_related)

    def test_selected_inclusions_are_cached_per_view(self):
        for selection, expected in (
            (
                {"zaaktype": {"catalogus": {"domein": None}}},
                "zaaktype,zaaktype.catalogus",
            ),
            ({"status": None}, ""),
        ):
            with self.subTest(selection=selection):
                request = SimpleNamespace(
                    method="POST", data={"fields": []}, query_params={}
                )
                view = ZaakViewSet()
                view.action = "_zoek"
                view._selected_fields = selection
                self.assertIsNone(view._selected_inclusions)
                with patch.object(
                    view, "get_serializer_class", wraps=view.get_serializer_class
                ) as get_serializer_class:
                    self.assertEqual(view.get_requested_inclusions(request), expected)
                    get_serializer_class.assert_called_once()
                    # Explicit expansions do not override cached field selections.
                    request.query_params["expand"] = "resultaat"
                    self.assertEqual(
                        view.get_requested_inclusions(request),
                        expected,
                    )
                    get_serializer_class.assert_called_once()

    def test_field_selection_uses_configured_response_serializer(self):
        class ResponseSerializer(serializers.Serializer):
            display_name = serializers.CharField()
            inclusion_serializers = {}

        class SearchFields(ZoekFieldsSerializer):
            parent_serializer_class = ResponseSerializer

        class SearchSerializer(serializers.Serializer):
            fields = SearchFields()

        serializer = SearchSerializer(data={"fields": ["displayName"]})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["fields"], {"display_name": None})

    def test_invalid_selections(self):
        messages = ZoekFieldsSerializer.default_error_messages
        for selection, message in (
            ([None], messages["invalid_selection"]),
            ([True], messages["invalid_selection"]),
            ([{}], messages["invalid_selection"]),
            (["unknown"], messages["unknown_field"].format(name="unknown")),
            (["_expand"], messages["unknown_field"].format(name="Expand")),
            ([{"uuid": ["url"]}], messages["not_nested"].format(name="uuid")),
            ([{"status": None}], messages["invalid_selection"]),
            (
                [{"status": ["unknown"]}],
                messages["unknown_field"].format(name="status.unknown"),
            ),
            ([{"*": ["url"]}], messages["unknown_field"].format(name="*")),
        ):
            with self.subTest(selection=selection):
                serializer = ZaakZoekSerializer(data={"fields": selection})
                self.assertFalse(serializer.is_valid())
                self.assertEqual(serializer.errors, {"fields": [message]})

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
        self.assertTrue(serializer.is_valid())
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


@tag("gh-2539")
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

    def test_all_fields_query_count_is_constant(self):
        # Select every registered inclusion and all fields at each level
        # Building the selection from the serializer also covers newly added paths
        selection = ["*"]
        for path in ZaakSerializer.inclusion_serializers:
            children = selection
            for name in path.split("."):
                nested = next(
                    (
                        entry[name]
                        for entry in children
                        if isinstance(entry, dict) and name in entry
                    ),
                    None,
                )
                if nested is None:
                    nested = ["*"]
                    children.append({name: nested})
                children = nested

        zaken = [ZaakFactory.create(hoofdzaak=ZaakFactory.create()) for _ in range(3)]
        for zaak in zaken:
            for instance in (zaak, zaak.hoofdzaak):
                StatusFactory.create(
                    zaak=instance, statustype__zaaktype=instance.zaaktype
                )
                ResultaatFactory.create(zaak=instance)
                RolFactory.create(zaak=instance)
                ZaakInformatieObjectFactory.create(zaak=instance)

        with CaptureQueriesContext(connection) as single_queries:
            single = self.search(selection, uuid__in=[str(zaken[0].uuid)])
        with CaptureQueriesContext(connection) as multiple_queries:
            multiple = self.search(
                selection, uuid__in=[str(zaak.uuid) for zaak in zaken]
            )

        self.assertEqual(single.status_code, status.HTTP_200_OK)
        self.assertEqual(multiple.status_code, status.HTTP_200_OK)
        data = multiple.json()
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(len(multiple_queries), len(single_queries))

    def test_fields_are_parsed_once_per_request(self):
        with patch.object(
            ZaakZoekFieldsSerializer,
            "to_internal_value",
            autospec=True,
            side_effect=ZaakZoekFieldsSerializer.to_internal_value,
        ) as parse:
            response = self.search([{"zaaktype": ["identificatie"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(parse.call_count, 1)

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
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()
                results = data["results"]
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            data["results"],
            [
                {
                    "uuid": str(zaak.uuid),
                    "verantwoordelijkeOrganisatie": zaak.verantwoordelijke_organisatie,
                }
                for zaak in reversed(zaken)
            ],
        )

    def test_selected_fields_without_pagination(self):
        with patch.object(ZaakViewSet, "pagination_class", None):
            response = self.search(["uuid"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data, [{"uuid": str(self.zaak.uuid)}])

    def test_existing_filters_still_apply(self):
        ZaakFactory.create()
        response = self.search(["uuid"], uuid__in=[str(self.zaak.uuid)])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(data, [{"uuid": str(self.zaak.uuid)}])

    def test_empty_results(self):
        response = self.search(["uuid"], uuid__in=[])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(data, [])

    def test_empty_selection(self):
        response = self.search([])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(data, [{}])

    def test_omitted_fields_and_wildcard_return_complete_response(self):
        complete = self.client.post(
            self.url, {"uuid__in": [str(self.zaak.uuid)]}, **POST_KWARGS
        )
        selected = self.search(["*"])

        complete_data = complete.json()
        data = selected.json()
        self.assertEqual(data, complete_data)
        self.assertIn("omschrijving", complete_data["results"][0])

    def test_expanded_url_is_not_added_to_parent(self):
        response = self.search([{"zaaktype": ["url", "omschrijving"]}])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype = self.zaak.zaaktype
        data = response.json()
        self.assertEqual(
            data["results"],
            [
                {
                    "_expand": {
                        "zaaktype": {
                            "url": self.check_for_instance(zaaktype),
                            "omschrijving": zaaktype.zaaktype_omschrijving,
                        }
                    }
                }
            ],
        )

    def test_relation_url_can_be_selected_alongside_expansion(self):
        for fields in (
            ["zaaktype", {"zaaktype": ["url"]}],
            [{"zaaktype": ["url"]}, "zaaktype"],
        ):
            with self.subTest(fields=fields):
                response = self.search(fields)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                url = self.check_for_instance(self.zaak.zaaktype)
                data = response.json()
                self.assertEqual(
                    data["results"],
                    [
                        {
                            "zaaktype": url,
                            "_expand": {"zaaktype": {"url": url}},
                        }
                    ],
                )

    def test_nested_relation_url_requires_explicit_selection(self):
        zaaktype = self.zaak.zaaktype
        response = self.search([{"zaaktype": [{"catalogus": ["domein"]}]}])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            data["results"],
            [
                {
                    "_expand": {
                        "zaaktype": {
                            "_expand": {
                                "catalogus": {"domein": zaaktype.catalogus.domein}
                            },
                        }
                    }
                }
            ],
        )

    def test_nested_relation_url_can_be_selected_alongside_expansion(self):
        catalogus = self.zaak.zaaktype.catalogus
        for fields in (
            ["catalogus", {"catalogus": ["url", "domein"]}],
            [{"catalogus": ["url", "domein"]}, "catalogus"],
        ):
            with self.subTest(fields=fields):
                response = self.search([{"zaaktype": fields}])
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                url = self.check_for_instance(catalogus)
                data = response.json()
                self.assertEqual(
                    data["results"],
                    [
                        {
                            "_expand": {
                                "zaaktype": {
                                    "catalogus": url,
                                    "_expand": {
                                        "catalogus": {
                                            "url": url,
                                            "domein": catalogus.domein,
                                        }
                                    },
                                }
                            }
                        }
                    ],
                )

    def test_catalogus_expansion_is_prefetched(self):
        ZaakFactory.create_batch(3)

        with CaptureQueriesContext(connection) as queries:
            response = self.search([{"zaaktype": [{"catalogus": ["domein"]}]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 4)
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
            self.assertEqual(
                single_response.status_code, status.HTTP_200_OK, single_response.data
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertLessEqual(len(queries) - len(single_queries), 2)
            relation_queries = [
                q["sql"] for q in queries if f"FROM {table}" in q["sql"]
            ]
            # Multiple expansion paths can prefetch the same table, but their
            # query count must remain independent of the number of zaken
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

        self.assertEqual(
            single_response.status_code, status.HTTP_200_OK, single_response.data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(len(multiple_queries), len(single_queries))
        for result in data["results"]:
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        result = data["results"][0]
        self.assertEqual(set(result), {"_expand"})
        self.assertEqual(result["_expand"]["status"]["uuid"], str(zaak_status.uuid))
        self.assertIn("datumStatusGezet", result["_expand"]["status"])

    def test_null_relation(self):
        response = self.search([{"resultaat": ["*"]}])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["results"], [{"resultaat": None}])

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
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(queries), len(single_queries))
                data = response.json()
                self.assertEqual(len(data["results"]), 3)
                for result in data["results"]:
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        relation = data["results"][0]["_expand"]["zaakinformatieobjecten"][0]
        self.assertEqual(set(relation), {"_expand"})
        self.assertEqual(
            relation["_expand"], {"informatieobject": {"bestandsnaam": "report-v2.pdf"}}
        )

    def test_document_fields_use_inclusion_viewset_prefetches(self):
        document = EnkelvoudigInformatieObjectFactory.create()
        ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=document.canonical
        )
        with CaptureQueriesContext(connection) as queries:
            response = self.search(
                [{"zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}]}]
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The document viewset prefetches file parts for all field selections.
        self.assertEqual(
            sum('FROM "documenten_bestandsdeel"' in q["sql"] for q in queries), 1
        )
        data = response.json()
        expanded = data["results"][0]["_expand"]["zaakinformatieobjecten"][0]
        self.assertEqual(
            expanded["_expand"]["informatieobject"],
            {"bestandsnaam": document.bestandsnaam},
        )

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
        data = response.json()
        expanded = data["results"][0]["_expand"]
        self.assertEqual(set(expanded["zaaktype"]), {"identificatie"})
        self.assertEqual(
            set(expanded["hoofdzaak"]["_expand"]["zaaktype"]), {"omschrijving"}
        )

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 3)
        self.assertEqual(len(multiple_queries), len(single_queries))
        for result in data["results"]:
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
                "status": ["uuid", {"statustype": ["volgnummer"]}],
                "resultaat": ["uuid"],
                "zaakinformatieobjecten": [{"informatieobject": ["bestandsnaam"]}],
                "processobject": ["identificatie"],
            },
        ]
        response = self.search(fields)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaak_url = self.check_for_instance(self.zaak)
        zaaktype = self.zaak.zaaktype

        data = response.json()
        self.assertEqual(
            data["results"],
            [
                {
                    "url": zaak_url,
                    "uuid": str(self.zaak.uuid),
                    "identificatie": self.zaak.identificatie,
                    "bronorganisatie": self.zaak.bronorganisatie,
                    "processobject": {
                        "identificatie": self.zaak.processobject_identificatie
                    },
                    "_expand": {
                        "zaaktype": {
                            "identificatie": zaaktype.identificatie,
                            "omschrijving": zaaktype.zaaktype_omschrijving,
                            "_expand": {
                                "catalogus": {"domein": zaaktype.catalogus.domein}
                            },
                        },
                        "status": {
                            "uuid": str(zaak_status.uuid),
                            "_expand": {
                                "statustype": {
                                    "volgnummer": zaak_status.statustype.statustypevolgnummer
                                }
                            },
                        },
                        "resultaat": {"uuid": str(resultaat.uuid)},
                        "zaakinformatieobjecten": [
                            {
                                "_expand": {
                                    "informatieobject": {"bestandsnaam": "report.pdf"}
                                },
                            }
                        ],
                    },
                }
            ],
        )

    def test_fields_and_expand_are_mutually_exclusive(self):
        for body, query_params in (
            ({"expand": ["zaaktype"]}, {}),
            ({}, {"expand": "zaaktype"}),
            ({}, {"expand": ""}),
        ):
            with self.subTest(body=body, query_params=query_params):
                response = self.search(["uuid"], query_params=query_params, **body)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], "invalid")
                error = get_validation_errors(response, "nonFieldErrors")
                self.assertEqual(error["code"], "invalid_field")
                self.assertEqual(
                    error["reason"],
                    "Het gebruik van het `fields` en `expand` element is mutual exclusive.",
                )

    def test_invalid_field_selections(self):
        for fields, code, error_path in (
            ("uuid", "not_a_list", None),
            ([True], "invalid_selection", None),
            (["doesNotExist"], "unknown_field", "doesNotExist"),
            ([{"uuid": ["url"]}], "not_nested", "uuid"),
            ([{"status": ["doesNotExist"]}], "unknown_field", "status.doesNotExist"),
        ):
            with self.subTest(fields=fields):
                response = self.search(fields)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], "invalid")
                error = get_validation_errors(response, "fields")
                self.assertEqual(error["code"], code)
                if error_path:
                    self.assertIn(error_path, error["reason"])

    def test_invalid_search_filter_with_fields(self):
        response = self.search(["uuid"], uuid__in=["invalid"])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid")
        # Older error formatters omit the first list index.
        error = get_validation_errors(response, "uuid__in.0") or get_validation_errors(
            response, "uuid__in."
        )
        self.assertIsNotNone(error)
        self.assertEqual(error["code"], "invalid")
        self.assertTrue(error["reason"])


@tag("gh-2539")
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["results"], [{"uuid": str(self.zaak.uuid)}])

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
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                authorization.delete()

    def test_plain_relation_url_does_not_require_expansion_scope(self):
        response = self.client.post(self.url, {"fields": ["zaaktype"]}, **POST_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            data["results"],
            [{"zaaktype": self.check_for_instance(self.zaaktype)}],
        )

    def test_selection_without_zaak_scope_is_forbidden(self):
        self.autorisatie.delete()
        response = self.client.post(self.url, {"fields": []}, **POST_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_omitted_expanded_field_is_rejected(self):
        response = self.client.post(
            self.url,
            {"fields": ["uuid"]},
            query_params={"expand": "zaaktype"},
            **POST_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertIsNotNone(error)
        self.assertEqual(error["code"], "invalid_field")
