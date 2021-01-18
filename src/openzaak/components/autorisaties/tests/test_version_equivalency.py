# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import SimpleTestCase

from ..utils import versions_equivalent


class VersionEquivalencyTests(SimpleTestCase):
    def test_empty_objects_equivalent(self):
        objects = (
            ({}, {}),
            ({"foo": []}, {"foo": []}),
            ({"bar": {}}, {"bar": {}}),
        )
        for obj1, obj2 in objects:
            with self.subTest(obj1=obj1, obj2=obj2):
                equivalent = versions_equivalent(obj1, obj2)

                self.assertTrue(equivalent)

    def test_simple_list_different_order(self):
        obj1 = {"list": [0, 1]}
        obj2 = {"list": [1, 0]}

        equivalent = versions_equivalent(obj1, obj2)

        self.assertTrue(equivalent)

    def test_simple_different_structures(self):
        objects = (
            ({}, {"foo": None}),
            ({"foo": []}, {"foo": ["bar"]}),
            ({"foo": []}, {"foo": ()}),
        )

        for obj1, obj2 in objects:
            with self.subTest(obj1=obj1, obj2=obj2):
                equivalent = versions_equivalent(obj1, obj2)

                self.assertFalse(equivalent)

    def test_list_of_dicts(self):
        obj1 = {
            "foo": [{"bar": 1}, {"baz": 2},],
        }
        obj2 = {
            "foo": [{"baz": 2}, {"bar": 1},],
        }

        equivalent = versions_equivalent(obj1, obj2)

        self.assertTrue(equivalent)

    def test_list_of_different_dicts(self):
        obj1 = {
            "foo": [{"bar": 1}, {"baz": 2},],
        }
        obj2 = {
            "foo": [{"bar": 1}, {"baz": 3},],
        }

        equivalent = versions_equivalent(obj1, obj2)

        self.assertFalse(equivalent)
