# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from unittest.mock import patch

from django.test import SimpleTestCase

from django_loose_fk.loaders import FetchError
from rest_framework import serializers, status
from rest_framework.test import APITestCase

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.api.serializers import (
    BesluitTypeSerializer,
    InformatieObjectTypeSerializer,
    ZaakTypeInformatieObjectTypeSerializer,
)
from openzaak.components.catalogi.models import (
    BesluitType,
    BesluitTypeInformatieObjectType,
    InformatieObjectType,
    ZaakTypeInformatieObjectType,
)
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.zaken.models import ZaakBesluit
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.expansion import (
    ExpandLoader,
    fields_at_path,
    limit_serializer_fields,
)
from openzaak.utils.urls import reverse


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
        informatieobjecttype = InformatieObjectType(pk=42)
        ztiot = ZaakTypeInformatieObjectType(
            _informatieobjecttype_id=informatieobjecttype.pk
        )
        loader = ExpandLoader(allowed_paths=None)
        loader._seen_local[
            (InformatieObjectTypeSerializer, informatieobjecttype.pk)
        ] = informatieobjecttype

        inclusions = list(
            loader._loose_fk_field_inclusions(
                ("informatieobjecttype",),
                ZaakTypeInformatieObjectTypeSerializer().fields["informatieobjecttype"],
                ztiot,
                InformatieObjectTypeSerializer,
            )
        )

        self.assertEqual(inclusions, [informatieobjecttype])
        self.assertIs(inclusions[0], informatieobjecttype)


EXTERNAL_IOTYPE = "https://external.catalogi.nl/api/v1/informatieobjecttypen/1"


class ExternalRelation:
    """
    Stand-in for a model instance with an external loose-fk reference, which counts
    how often the reference is loaded through the model field descriptor
    """

    def __init__(self, loaded=None, error: Exception | None = None):
        self._iotype_url = EXTERNAL_IOTYPE
        self._loaded = loaded
        self._error = error
        self.loads = 0

    @property
    def informatieobjecttype(self):
        self.loads += 1
        if self._error:
            raise self._error
        return self._loaded


class ExpandLoaderLooseFkTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.loader = ExpandLoader(allowed_paths=None)

    def _include(self, field, instance, path=("informatieobjecttype",)):
        return list(
            self.loader._loose_fk_field_inclusions(
                path, field, instance, InformatieObjectTypeSerializer
            )
        )

    def test_external_relation_is_loaded_once(self):
        field = ZaakTypeInformatieObjectTypeSerializer().fields["informatieobjecttype"]
        external = object()
        first = ExternalRelation(loaded=external)
        second = ExternalRelation(loaded=object())

        self.assertEqual(self._include(field, first), [external])
        self.assertEqual(self._include(field, second), [external])

        self.assertEqual(first.loads, 1)
        self.assertEqual(second.loads, 0)

    def test_external_relation_that_cannot_be_fetched_is_skipped(self):
        field = ZaakTypeInformatieObjectTypeSerializer().fields["informatieobjecttype"]
        relation = ExternalRelation(error=FetchError("not found"))

        self.assertEqual(self._include(field, relation), [])
        self.assertNotIn(EXTERNAL_IOTYPE, self.loader._seen_external)


class ExpandLoaderLooseFkListTests(SimpleTestCase):
    """
    besluittype.informatieobjecttypen is a list of loose-fk references, stored on
    the BesluitTypeInformatieObjectType through model
    """

    def setUp(self):
        super().setUp()
        self.loader = ExpandLoader(allowed_paths=None)
        self.field = BesluitTypeSerializer().fields["informatieobjecttypen"]
        self.besluittype = BesluitType(pk=1)

    def _include(self, relations):
        with patch.object(self.field, "get_relations", return_value=relations):
            return list(
                self.loader._loose_fk_field_inclusions(
                    ("informatieobjecttypen",),
                    self.field,
                    self.besluittype,
                    InformatieObjectTypeSerializer,
                )
            )

    def test_local_relations(self):
        iotype1 = InformatieObjectType(pk=1)
        iotype2 = InformatieObjectType(pk=2)

        inclusions = self._include(
            [
                BesluitTypeInformatieObjectType(_informatieobjecttype=iotype1),
                BesluitTypeInformatieObjectType(_informatieobjecttype=iotype2),
            ]
        )

        self.assertEqual(inclusions, [iotype1, iotype2])
        self.assertIs(
            self.loader._seen_local[(InformatieObjectTypeSerializer, 2)], iotype2
        )

    def test_local_relation_reuses_cached_instance_without_query(self):
        iotype = InformatieObjectType(pk=42)
        self.loader._seen_local[(InformatieObjectTypeSerializer, iotype.pk)] = iotype

        inclusions = self._include(
            [BesluitTypeInformatieObjectType(_informatieobjecttype_id=iotype.pk)]
        )

        self.assertEqual(inclusions, [iotype])
        self.assertIs(inclusions[0], iotype)

    def test_local_and_external_relations(self):
        iotype = InformatieObjectType(pk=1)
        external = object()
        external_relation = ExternalRelation(loaded=external)

        inclusions = self._include(
            [
                BesluitTypeInformatieObjectType(_informatieobjecttype=iotype),
                external_relation,
                ExternalRelation(loaded=object()),
            ]
        )

        self.assertEqual(inclusions, [iotype, external, external])
        self.assertEqual(external_relation.loads, 1)

    def test_external_relation_that_cannot_be_fetched_is_skipped(self):
        iotype = InformatieObjectType(pk=1)

        inclusions = self._include(
            [
                ExternalRelation(error=FetchError("not found")),
                BesluitTypeInformatieObjectType(_informatieobjecttype=iotype),
            ]
        )

        self.assertEqual(inclusions, [iotype])

    def test_no_relations(self):
        self.assertEqual(self._include([]), [])

    def test_list_field_inclusions_are_many(self):
        iotype = InformatieObjectType(pk=1)
        relations = [BesluitTypeInformatieObjectType(_informatieobjecttype=iotype)]

        with patch.object(self.field, "get_relations", return_value=relations):
            obj, inclusion_serializer, parent, path, many = next(
                self.loader._field_inclusions(
                    (),
                    self.field,
                    self.besluittype,
                    "informatieobjecttypen",
                    {"informatieobjecttypen": InformatieObjectTypeSerializer},
                )
            )

        self.assertIs(obj, iotype)
        self.assertIs(inclusion_serializer, InformatieObjectTypeSerializer)
        self.assertIs(parent, self.besluittype)
        self.assertEqual(path, ("informatieobjecttypen",))
        self.assertTrue(many)


class ExpandNamespaceTests(JWTAuthMixin, APITestCase):
    """
    Moved resources are served under multiple namespaces (besluittypen under
    `catalogi` and `zaken`, informatieobjecttypen under `catalogi` and `documenten`).
    The expansions have to be linked to the urls as rendered in the response, which
    depend on the namespace of the request.
    """

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.catalogus = CatalogusFactory.create()
        cls.besluittype = BesluitTypeFactory.create(
            catalogus=cls.catalogus, concept=False
        )
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=cls.catalogus, concept=False
        )
        cls.besluittype.informatieobjecttypen.add(cls.informatieobjecttype)

    def url(self, obj, namespace: str | None = None) -> str:
        """
        Absolute url of `obj`, by default in the namespace of its app
        """
        namespace = namespace or obj._meta.app_label
        return f"http://testserver{reverse(obj, namespace=namespace)}"

    def assertExpanded(self, data: dict, field: str, expected: str | list[str]):
        """
        Assert both the link(s) in the resource and the url(s) of the expansion are
        the expected urls
        """
        self.assertEqual(data[field], expected)

        self.assertIn("_expand", data)
        self.assertIn(field, data["_expand"])
        expanded = data["_expand"][field]

        if isinstance(expected, list):
            self.assertEqual([item["url"] for item in expanded], expected)
        else:
            self.assertEqual(expanded["url"], expected)

    def _get(self, url, expand: str):
        response = self.client.get(url, {"expand": expand})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()

    def test_besluittype(self):
        # (namespace of the request, namespace of the informatieobjecttype links)
        cases = (
            ("catalogi", "catalogi"),
            ("zaken", "documenten"),
        )
        for namespace, iotype_namespace in cases:
            for detail in (True, False):
                with self.subTest(namespace=namespace, detail=detail):
                    if detail:
                        data = self._get(
                            self.url(self.besluittype, namespace),
                            "catalogus,informatieobjecttypen",
                        )
                    else:
                        (data,) = self._get(
                            reverse(BesluitType, namespace=namespace),
                            "catalogus,informatieobjecttypen",
                        )["results"]

                    self.assertEqual(data["url"], self.url(self.besluittype, namespace))
                    self.assertExpanded(
                        data, "catalogus", self.url(self.catalogus, namespace)
                    )
                    self.assertExpanded(
                        data,
                        "informatieobjecttypen",
                        [self.url(self.informatieobjecttype, iotype_namespace)],
                    )

    def test_informatieobjecttype(self):
        # (namespace of the request, namespace of the besluittype links)
        cases = (
            ("catalogi", "catalogi"),
            ("documenten", "zaken"),
        )
        for iot_namespace, namespace in cases:
            for detail in (True, False):
                with self.subTest(namespace=iot_namespace, detail=detail):
                    if detail:
                        data = self._get(
                            self.url(self.informatieobjecttype, iot_namespace),
                            "catalogus,besluittypen",
                        )
                    else:
                        (data,) = self._get(
                            reverse(InformatieObjectType, namespace=iot_namespace),
                            "catalogus,besluittypen",
                        )["results"]

                    self.assertEqual(
                        data["url"], self.url(self.informatieobjecttype, iot_namespace)
                    )
                    self.assertExpanded(
                        data, "catalogus", self.url(self.catalogus, namespace)
                    )
                    self.assertExpanded(
                        data,
                        "besluittypen",
                        [self.url(self.besluittype, namespace)],
                    )

    def test_nested_resource(self):
        """
        The url of a nested resource (zaken/{zaak_uuid}/besluiten/{uuid}) is
        rendered by the serializer, including the parent uuid.
        """
        besluit = BesluitFactory.create(for_zaak=True)
        zaakbesluit = ZaakBesluit.objects.get(besluit=besluit)
        url = reverse(
            "zaken:zaakbesluit-detail",
            kwargs={"zaak_uuid": besluit.zaak.uuid, "uuid": zaakbesluit.uuid},
        )

        data = self._get(url, "besluit")

        self.assertEqual(data["url"], f"http://testserver{url}")
        self.assertExpanded(data, "besluit", self.url(besluit, "zaken"))
