# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test the JSON output/formatting principles.
"""
import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView


class View(APIView):
    def get(self, request, *args, **kwargs):
        data = {"snake_case": "value"}
        return Response(data)

    def put(self, request, *args, **kwargs):
        request.data
        return self.get(request)


class NoContentTypeRequestFactory(APIRequestFactory):
    def generic(self, method, path, data="", content_type=None, secure=False, **extra):
        if "CONTENT_TYPE" in extra:
            del extra["CONTENT_TYPE"]
        request = super().generic(
            method, path, data, content_type=None, secure=secure, **extra
        )
        return request

    def request(self, **request):
        if "CONTENT_TYPE" in request:
            del request["CONTENT_TYPE"]
        return super().request(**request)


class JSONFormatTests(APITestCase):

    factory = APIRequestFactory()

    def _get_response(self, request=None):
        _view = View.as_view()
        request = request or self.factory.get("/foo")
        response = _view(request)
        response.render()

        # quick access
        response.json = lambda: json.loads(response.content)

        return response

    def test_accept_and_return_json(self):
        """
        DSO: API-26 (accept and return JSON)
        """
        response = self._get_response()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_content_type_header_is_required(self):
        """
        DSO: API-29 (content type header is required)

        Typically, this header is passed on POST/PUT/PATCH requests to indicate
        the body content type.
        """
        # results in no CT header
        request = NoContentTypeRequestFactory().put("/foo", data={"foo": "bar"})

        response = self._get_response(request=request)

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_camelcase_field_names(self):
        """
        DSO: API-30 (camelCase field names)
        """
        response = self._get_response()

        rendered = response.json()
        self.assertIn("snakeCase", rendered)

    def test_no_pretty_print(self):
        """
        DSO: API-31 (no pretty print)
        """
        response = self._get_response()

        raw_data = response.content.decode("utf-8")
        self.assertNotIn("  ", raw_data)
        self.assertNotIn("\n", raw_data)

    def test_no_envelope(self):
        """
        DSO: API-32 (no envelope)

        # NOTE: List resources do have envelopes, even suggested by DSO.
        """
        response = self._get_response()

        data = response.json()
        self.assertEqual(list(data.keys()), ["snakeCase"])

    def test_content_type_json_is_supported(self):
        """
        DSO: API-33 (content type application/json is supported)
        """
        content_types = ["application/json", "application/json; charset=utf-8"]
        for ct in content_types:
            with self.subTest(content_type=ct):
                request = self.factory.get("/foo", content_type=ct)

                response = self._get_response(request=request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_content_type_x_is_not_supported(self):
        """
        DSO: API-33 (content type application/x-www-form-urlencoded is not supported)
        """
        invalid_content_types = [
            "application/x-www-form-urlencoded",
            "application/xml",
            "text/html",
        ]

        for ct in invalid_content_types:
            with self.subTest(content_type=ct):
                request = self.factory.put("/foo", data={"foo": "bar"}, content_type=ct)

                response = self._get_response(request=request)

                self.assertEqual(
                    response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                )
