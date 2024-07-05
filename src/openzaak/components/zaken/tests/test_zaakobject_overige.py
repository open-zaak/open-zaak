# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.test import tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ZaakobjectTypes

from openzaak.tests.utils import JWTAuthMixin

from ..models import ZaakObject
from ..tests.factories import ZaakFactory
from ..tests.utils import get_operation_url


@tag("objecttype-overige-definitie")
class ZaakObjectObjectTypeOverigeDefinitie(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    OBJECT_TYPE = {
        "url": "https://objecttypes.example.com/api/objecttypes/foo",
        "version": 123,
        "jsonSchema": {
            "$schema": "http://json-schema.org/draft-07/schema",
            "$id": "http://gemeente.nl/beleidsveld.json",
            "type": "object",
            "title": "Beleidsvelden",
            "description": "Beleidsvelden in gebruik binnen de gemeente",
            "default": {},
            "examples": [
                {"name": "Burgerzaken"},
            ],
            "required": ["name"],
            "properties": {
                "name": {
                    "$id": "#/properties/name",
                    "type": "string",
                    "title": "The name schema",
                    "default": "",
                    "examples": ["Burgerzaken"],
                    "maxLength": 100,
                    "minLength": 1,
                    "description": "The name identifying each beleidsveld.",
                },
            },
            "additionalProperties": False,
        },
    }

    @requests_mock.Mocker()
    def test_create_zaakobject_overig_explicit_schema(self, m):
        """
        Assert that external object type definitions can be referenced.
        """
        object_url = "https://objects.example.com/api/objects/1234"
        m.get(
            "https://objecttypes.example.com/api/objecttypes/foo", json=self.OBJECT_TYPE
        )
        m.get(
            object_url,
            json={
                "url": object_url,
                "type": "https://objecttypes.example.com/api/objecttypes/foo",
                "record": {
                    "data": {
                        "name": "Asiel en Migratie",
                    }
                },
            },
        )

        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": object_url,
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverigeDefinitie": {
                "url": "https://objecttypes.example.com/api/objecttypes/foo",
                # https://stedolan.github.io/jq/ format
                "schema": ".jsonSchema",
                "objectData": ".record.data",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())

        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.object, object_url)
        self.assertEqual(
            zaakobject.object_type_overige_definitie,
            {
                "url": "https://objecttypes.example.com/api/objecttypes/foo",
                # https://stedolan.github.io/jq/ format
                "schema": ".jsonSchema",
                "object_data": ".record.data",
            },
        )

    @requests_mock.Mocker()
    def test_invalid_schema_reference(self, m):
        object_url = "https://objects.example.com/api/objects/1234"
        m.get(
            "https://objecttypes.example.com/api/objecttypes/foo", json=self.OBJECT_TYPE
        )
        m.get(
            object_url,
            json={
                "url": object_url,
                "type": "https://objecttypes.example.com/api/objecttypes/foo",
                "record": {
                    "data": {
                        "name": "Asiel en Migratie",
                    }
                },
            },
        )

        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": object_url,
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverigeDefinitie": {
                "url": "https://objecttypes.example.com/api/objecttypes/foo",
                # https://stedolan.github.io/jq/ format
                "schema": ".invalid",
                "objectData": ".record.data",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )

    @requests_mock.Mocker()
    def test_invalid_object_url_passed(self, m):
        object_url = "https://objects.example.com/api/objects/1234"
        m.get(
            "https://objecttypes.example.com/api/objecttypes/foo", json=self.OBJECT_TYPE
        )
        m.get(
            object_url,
            json={
                "url": object_url,
                "type": "https://objecttypes.example.com/api/objecttypes/foo",
                "record": {
                    "data": {
                        "invalidKey": "should not validate",
                    }
                },
            },
        )

        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "object": object_url,
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverigeDefinitie": {
                "url": "https://objecttypes.example.com/api/objecttypes/foo",
                # https://stedolan.github.io/jq/ format
                "schema": ".jsonSchema",
                "objectData": ".record.data",
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.json()
        )
