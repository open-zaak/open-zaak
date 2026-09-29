# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from vng_api_common.constants import ComponentTypes

from openzaak.components.besluiten.api.scopes import SCOPE_BESLUITEN_ALLES_LEZEN
from openzaak.components.catalogi.api.scopes import SCOPE_CATALOGI_READ
from openzaak.components.zaken.api.viewsets import ZaakViewSet
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.permissions import (
    AuthComponentTypeScopesRequired,
    AuthRequired,
    MultipleObjectsAuthRequired,
)


class AuthRequiredTests(TestCase):
    def setUp(self):
        self.auth = AuthRequired()

    def test_main_resource_missing(self):
        with self.assertRaises(ImproperlyConfigured):
            self.auth.get_main_resource(None)

    @override_settings(DEBUG=True)
    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_bypass(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        drf_request.accepted_renderer = BrowsableAPIRenderer()
        view = ZaakViewSet()
        result = self.auth.has_permission(drf_request, view)

        self.assertTrue(result)


class MultipleObjectsAuthRequiredTests(TestCase):
    def setUp(self):
        self.auth = MultipleObjectsAuthRequired()
        self.object = ZaakFactory.create()

    @override_settings(DEBUG=True)
    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_bypass(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        drf_request.accepted_renderer = BrowsableAPIRenderer()
        view = ZaakViewSet()

        result = self.auth.has_permission(drf_request, view)
        self.assertTrue(result)

        obj_result = self.auth.has_object_permission(drf_request, view, self.object)
        self.assertTrue(obj_result)

    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_viewset_classes_missing(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        view = ZaakViewSet()
        view.action = "list"
        view.viewset_classes = None

        result = self.auth.has_permission(drf_request, view)
        self.assertFalse(result)

        obj_result = self.auth.has_object_permission(drf_request, view, self.object)
        self.assertFalse(obj_result)

    @patch("openzaak.utils.permissions.AuthRequired.has_handler", return_value=None)
    def test_view_ismixin_and_action_none(self, mock_has_handler):
        factory = APIRequestFactory()
        django_request = factory.get("/some-url/")

        drf_request = Request(django_request)
        view = ZaakViewSet()
        view.action = None

        result = self.auth.has_permission(drf_request, view)

        self.assertTrue(result)


class AuthComponentTypeScopesRequiredTests(SimpleTestCase):
    def setUp(self):
        self.permission = AuthComponentTypeScopesRequired()
        self.request = SimpleNamespace(jwt_auth=Mock())
        self.view = SimpleNamespace(
            required_component_type_scopes={
                ComponentTypes.ztc: SCOPE_CATALOGI_READ,
                ComponentTypes.brc: SCOPE_BESLUITEN_ALLES_LEZEN,
            }
        )

    def test_all_component_scopes_are_authorized(self):
        self.request.jwt_auth.has_auth.return_value = True

        self.assertTrue(self.permission.has_permission(self.request, self.view))
        self.assertEqual(
            self.request.jwt_auth.has_auth.call_args_list,
            [
                call(SCOPE_CATALOGI_READ, ComponentTypes.ztc),
                call(SCOPE_BESLUITEN_ALLES_LEZEN, ComponentTypes.brc),
            ],
        )

    def test_any_missing_component_scope_denies_access(self):
        for denied_component in self.view.required_component_type_scopes:
            with self.subTest(component=denied_component):
                self.request.jwt_auth.has_auth.side_effect = (
                    lambda scopes, component: component != denied_component
                )
                self.assertFalse(
                    self.permission.has_permission(self.request, self.view)
                )

    def test_object_restrictions_are_passed_to_jwt_auth(self):
        self.view.required_component_type_scopes = {
            ComponentTypes.brc: SCOPE_BESLUITEN_ALLES_LEZEN,
        }
        fields = [
            {"besluittype": "http://testserver/type/1"},
            {"besluittype": "http://testserver/type/2"},
        ]
        self.request.jwt_auth.has_auth.side_effect = [True, False]
        with patch.object(
            self.permission, "get_component_permission_fields", return_value=fields
        ):
            self.assertFalse(self.permission.has_permission(self.request, self.view))
        self.assertEqual(
            self.request.jwt_auth.has_auth.call_args_list,
            [
                call(SCOPE_BESLUITEN_ALLES_LEZEN, ComponentTypes.brc, **item)
                for item in fields
            ],
        )

    def test_component_is_required_even_without_objects(self):
        self.request.jwt_auth.has_auth.return_value = False
        with patch.object(
            self.permission, "get_component_permission_fields", return_value=[]
        ):
            self.assertFalse(self.permission.has_permission(self.request, self.view))
        self.request.jwt_auth.has_auth.assert_called_once_with(
            SCOPE_CATALOGI_READ,
            ComponentTypes.ztc,
        )

    def test_required_component_scopes_must_be_configured(self):
        for view in (
            SimpleNamespace(),
            SimpleNamespace(required_component_type_scopes={}),
        ):
            with self.subTest(view=view):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "must define required_component_type_scopes"
                ):
                    self.permission.has_permission(self.request, view)
