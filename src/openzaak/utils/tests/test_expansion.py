# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import SimpleTestCase

from rest_framework import serializers

from openzaak.components.catalogi.api.serializers import ZaakTypeSerializer
from openzaak.components.catalogi.models import ZaakType
from openzaak.components.zaken.api.serializers import ZaakSerializer
from openzaak.components.zaken.models import Zaak
from openzaak.utils.expansion import (
    ExpandLoader,
    fields_at_path,
    limit_serializer_fields,
)


class FieldSelectionTests(SimpleTestCase):
    def test_unselected_parent_stops_nested_lookup(self):
        self.assertIsNone(fields_at_path({"status": None}, ("status", "statustype")))
        self.assertIsNone(fields_at_path(None, ("status",)))

    def test_missing_path_is_not_selected(self):
        self.assertIsNone(fields_at_path({"uuid": None}, ("status",)))

    def test_root_and_nested_selections(self):
        selection = {"status": {"statustype": {"volgnummer": None}}}
        self.assertIs(fields_at_path(selection, ()), selection)
        self.assertEqual(
            fields_at_path(selection, ("status", "statustype")),
            {"volgnummer": None},
        )

    def test_nested_list_serializer_keeps_urls_and_selected_fields(self):
        # URLs are needed to link expanded resources
        # ExpandJSONRenderer removes them from the final response
        # unless requested explicitly or through '*'
        class ChildSerializer(serializers.Serializer):
            url = serializers.URLField()
            name = serializers.CharField()
            description = serializers.CharField()

        class ParentSerializer(serializers.Serializer):
            url = serializers.URLField()
            children = ChildSerializer(many=True)
            title = serializers.CharField()

        serializer = ParentSerializer(many=True)
        limit_serializer_fields(serializer, {"children": {"name": None}})

        self.assertEqual(set(serializer.child.fields), {"url", "children"})
        self.assertEqual(
            set(serializer.child.fields["children"].child.fields), {"url", "name"}
        )

    def test_wildcard_keeps_all_fields(self):
        class ResponseSerializer(serializers.Serializer):
            url = serializers.URLField()
            name = serializers.CharField()

        serializer = ResponseSerializer()
        self.assertIs(limit_serializer_fields(serializer, {"*": None}), serializer)
        self.assertEqual(set(serializer.fields), {"url", "name"})


class ExpandLoaderCacheTests(SimpleTestCase):
    def test_shared_local_relation_reuses_cached_instance_without_query(self):
        zaaktype = ZaakType(pk=42)
        zaak = Zaak(_zaaktype_id=zaaktype.pk)
        loader = ExpandLoader(allowed_paths=None)
        loader._seen_local[(ZaakTypeSerializer, zaaktype.pk)] = zaaktype

        inclusions = list(
            loader._loose_fk_field_inclusions(
                ("zaaktype",),
                ZaakSerializer().fields["zaaktype"],
                zaak,
                ZaakTypeSerializer,
            )
        )

        self.assertEqual(inclusions, [zaaktype])
        self.assertIs(inclusions[0], zaaktype)
