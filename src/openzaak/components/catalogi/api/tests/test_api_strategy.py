import json
from unittest import expectedFailure, skip, skipIf

from django.utils.translation import ugettext_lazy as _

import yaml
from rest_framework.settings import api_settings
from rest_framework.test import APILiveServerTestCase, APIRequestFactory
from vng_api_common.tests import reverse

from ...models import Catalogus
from ...models.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from . import views
from .base import APITestCase, CatalogusAPITestMixin
from .utils import get_operation_url


class RestfulPrinciplesAPITests(APITestCase):
    """Section 2.6.1 of the DSO: API strategy"""

    @skip("API structure is flat. There are no nested resources now")
    def test_nested_resources(self):
        """DSO: API-09 (nested resources)

        A ``ZaakType`` object can only be part of a ``Catalogus`` object.
        Hence, it should be nested under the ``catalogussen`` resource:
        ``/api/v1/catalogussen/{uuid}/zaaktypen``.
        """
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        kwargs = {"catalogus_uuid": self.catalogus.uuid, "uuid": zaaktype.uuid}
        zaaktype_detail_url = get_operation_url("zaaktype_read", **kwargs)

        self.assertEqual(
            zaaktype_detail_url,
            "/api/v1/catalogussen/{catalogus_uuid}/zaaktypen/{uuid}".format(**kwargs),
        )

    @skip("Not MVP")
    def test_expand_all_resources(self):
        """DSO: API-10 (expand all resources)

        Passing `/api/v1/catalogussen/1/?expand=true` expands all (1st level)
        expandable resources.
        """
        ZaakTypeFactory.create(catalogus=self.catalogus)

        # TODO: Why is this an English term, while search and ordering are Dutch?
        response = self.client.get(self.catalogus_detail_url, {"expand": "true"})
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # TODO: Extend with other resources.
        expected_expanded_resources = ["bestaatuitZaaktype"]
        for resource in expected_expanded_resources:
            with self.subTest(resource=resource):
                self.assertGreater(len(data[resource]), 0, data[resource])
                self.assertIsInstance(data[resource][0], dict)

    @skip("Not MVP")
    def test_expand_single_resource(self):
        """DSO: API-11 (expand single resource)

        Passing ``/api/v1/catalogussen/1/?expand=bestaatuitZaaktype`` expands
        only the resource referenced by the field "besluittypen".
        """
        ZaakTypeFactory.create(catalogus=self.catalogus)

        response = self.client.get(
            self.catalogus_detail_url, {"expand": "bestaatuitZaaktype"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        expected_expanded_resource = "bestaatuitZaaktype"
        self.assertGreater(len(data[expected_expanded_resource]), 0)
        self.assertIsInstance(data[expected_expanded_resource][0], dict)

        # TODO: Extend with other resources.
        expected_closed_resources = []  # ['bestaatuitInformatieobjecttype']
        for resource in expected_closed_resources:
            self.assertGreater(len(data[resource]), 0)
            self.assertIsInstance(data[resource][0], str)
            self.assertTrue(data[resource][0].startswith("http://"))

    @skip("Only bestaatuitZaaktype is currently enabled")
    def test_expand_multiple_resources(self):
        """DSO: API-11 (expand multiple resources)

        Passing ``/api/v1/catalogussen/1/?expand=bestaatuitBesluittype,bestaatuitInformatieobjecttype``
        expands only the two resources referenced by the field "besluittypen" and "informatieobjecttypen".
        """
        BesluitTypeFactory.create(catalogus=self.catalogus, publicatie_indicatie="J")
        InformatieObjectTypeFactory.create(catalogus=self.catalogus)

        response = self.client.get(
            self.catalogus_detail_url,
            {"expand": "bestaatuitBesluittype,bestaatuitInformatieobjecttype"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # TODO: Extend with other resources.
        expected_expanded_resources = [
            "bestaatuitBesluittype",
            "bestaatuitInformatieobjecttype",
        ]
        for resource in expected_expanded_resources:
            self.assertGreater(len(data[resource]), 0)
            self.assertIsInstance(data[resource][0], dict)

        # TODO: Extend with other resources.
        expected_closed_resources = []
        for resource in expected_closed_resources:
            self.assertGreater(len(data[resource]), 0)
            self.assertIsInstance(data[resource][0], str)
            self.assertTrue(data[resource][0].startswith("http://"))

    @skip("Not MVP")
    def test_expand_resource_with_specific_field(self):
        """DSO: API-11 (expand resource with specific field)

        Passing ``/api/v1/catalogussen/1/?expand=bestaatuitZaaktype.omschrijving`` expands only the resource
        referenced by the field "besluittypen" and only shows the field "omschrijving" of that resource.
        """
        ZaakTypeFactory.create(catalogus=self.catalogus)

        response = self.client.get(
            self.catalogus_detail_url, {"expand": "bestaatuitZaaktype.omschrijving"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        expected_expanded_resource = "bestaatuitZaaktype"
        self.assertGreater(len(data[expected_expanded_resource]), 0)
        self.assertIsInstance(data[expected_expanded_resource][0], dict)
        self.assertEqual(len(data[expected_expanded_resource][0]), 1)
        self.assertTrue("omschrijving" in data[expected_expanded_resource][0])

        # TODO: Extend with other resources.
        expected_closed_resources = []
        for resource in expected_closed_resources:
            self.assertGreater(len(data[resource]), 0)
            self.assertIsInstance(data[resource][0], str)
            self.assertTrue(data[resource][0].startswith("http://"))

    @skip("Not MVP")
    def test_specific_single_field(self):
        """DSO: API-12 (specific single field)

        Passing `/api/v1/catalogussen/1/?fields=domein` should only show the resource with the field "domein".
        """
        # TODO: Why is this an English term, while search and ordering are Dutch?
        response = self.client.get("{}?fields=domein".format(self.catalogus_detail_url))
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertTrue("domein" in data)

    @skip("Not MVP")
    def test_specific_multiple_fields(self):
        """DSO: API-12 (specific multiple fields)

        Passing `/api/v1/catalogussen/1/?fields=domein,rsin` should only show the resource with the 2 fields "domein"
        and "rsin".
        """
        response = self.client.get(
            "{}?fields=domein,rsin".format(self.catalogus_detail_url)
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(len(data), 2)
        self.assertTrue("domein" in data)
        self.assertTrue("rsin" in data)

    @expectedFailure
    def test_specific_unknown_field(self):
        """DSO: API-12 (specific unknown field)

        Passing `/api/v1/catalogussen/1/?fields=foobar` should return a HTTP 400 because the field "foobar" does not
        exist on the catalog resource.
        """
        response = self.client.get("{}?fields=foobar".format(self.catalogus_detail_url))
        self.assertEqual(response.status_code, 400)


class SecurityAPITests(CatalogusAPITestMixin, APILiveServerTestCase):
    """Section 2.6.2 of the DSO: API strategy"""

    def setUp(self):
        super().setUp()

        # Remove credentials from client
        self.client.credentials()

    def test_api_key_required(self):
        """DSO: API-15 (API key required)

        A valid API key is required to access any resource.
        """
        response = self.client.get(self.catalogus_list_url)
        self.assertEqual(response.status_code, 403)

    @skip("We do not use OAUTH but JWT based OAUTH")
    def test_disallow_token_in_query_params(self):
        """DSO: API-16 (disallow token in query params)

        It's not allowed to pass the API key/token via the URL as query parameter.
        """
        # Create a token without the whole authentication flow.
        pass

    @skip("We do not use OAUTH but JWT based OAUTH")
    def test_oauth2_authentication(self):
        """DSO: API-17 (OAuth2 authentication)

        Test the entire backend application flow:
        https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#backend-application-flow
        """
        pass


class DocumentationAPITests(APITestCase):
    """Section 2.6.3 of the DSO: API strategy"""

    schema_url = reverse("schema-redoc-catalogi")

    def test_documentation_is_oas_2(self):
        """DSO: API-19 (documentation is OAS 2)"""
        response = self.client.get("{}?format=openapi".format(self.schema_url))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode("utf-8"))

        self.assertTrue("swagger" in data)
        self.assertEqual(data["swagger"], "2.0")

    def test_api_19_documentation_version_json(self):
        url = reverse("schema-json-catalogi", kwargs={"format": ".json"})

        response = self.client.get(url)

        self.assertIn("application/json", response["Content-Type"])

        doc = response.json()

        self.assertGreaterEqual(doc["openapi"], "3.0.0")

    def test_api_19_documentation_version_yaml(self):
        url = reverse("schema-json-catalogi", kwargs={"format": ".yaml"})

        response = self.client.get(url)

        self.assertIn("application/yaml", response["Content-Type"])

        doc = yaml.safe_load(response.content)

        self.assertGreaterEqual(doc["openapi"], "3.0.0")

    def test_documentation_can_be_accepted(self):
        """DSO: API-21 (documentation can be tested)

        This topic is interpreted as the availability of an HTML "document" for the API specification. If you point
        your browser to the schema URL, a nice web page will be shown.
        """
        response = self.client.get(self.schema_url, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<html>")


class VersioningAPITests(APITestCase):
    """Section 2.6.4 of the DSO: API strategy"""

    def test_major_api_version_in_url(self):
        """DSO: API-24 (major API version in URL)"""
        self.assertTrue(
            "/v{}/".format(api_settings.DEFAULT_VERSION) in self.catalogus_list_url
        )

    @skip("Not MVP")
    def test_full_api_version_in_response_header(self):
        """DSO: API-24 (full API version in response header)"""
        response = self.client.get(self.catalogus_list_url)
        self.assertEqual(response.status_code, 200)

        self.assertIn("API-version", response)
        self.assertEqual(response["API-version"], "1.0.0-alpha")

    @skipIf(
        api_settings.DEFAULT_VERSION == "1",
        "Deprecated API versions should be tested once we get there.",
    )
    def test_deprecated_api_version_warning(self):
        """DSO: API-25 (deprecated API version warning)"""
        pass


class UseJSONTests(APITestCase):
    """Section 2.6.5 of the DSO: API strategy"""

    def test_accept_and_return_json(self):
        """DSO: API-26 (accept and return JSON)"""
        response = self.client.get(self.catalogus_list_url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response["content-type"], "application/json")

    @skip("Optional and currently not supported.")
    def test_json_schema_support(self):
        """DSO: API-27 (JSON-schema support)"""
        pass

    @skip("Optional and currently not supported.")
    def test_content_negotiation_xml(self):
        """DSO: API-28 (content negotiation XML)"""
        pass

    @skip("Optional and currently not supported.")
    def test_content_negotiation_unsupported_format(self):
        """DSO: API-28 (content negotiation unsupported format)"""
        response = self.client.get(self.catalogus_list_url, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 406)

    @skip("This API is currently read-only.")
    def test_content_type_header_is_required(self):
        """DSO: API-29 (content type header is required)

        Typically, this header is passed on POST/PUT/PATCH requests to indicate the body content type.
        """
        response = self.client.put(
            self.catalogus_detail_url, "{}", content_type="text/html"
        )
        self.assertEqual(response.status_code, 415)

    def test_camelcase_field_names(self):
        """DSO: API-30 (camelCase field names)"""
        response = self.client.get(self.catalogus_detail_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("contactpersoonBeheerNaam" in data)

    def test_no_pretty_print(self):
        """DSO: API-31 (no pretty print)"""
        response = self.client.get(self.catalogus_detail_url)
        self.assertEqual(response.status_code, 200)

        raw_data = response.content.decode("utf-8")

        self.assertFalse("  " in raw_data, raw_data)
        self.assertFalse("\n" in raw_data)

    def test_no_envelope(self):
        """DSO: API-32 (no envelope)"""
        # TODO: List resources do have envelopes, even suggested by DSO.
        response = self.client.get(self.catalogus_detail_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("contactpersoonBeheerNaam" in data)

    @skip("This API is currently read-only.")
    def test_content_type_json_is_supported(self):
        """DSO: API-33 (content type application/json is supported)"""
        response = self.client.patch(self.catalogus_detail_url, "{}")
        self.assertEqual(response.status_code, 200)

        response = self.client.put(self.catalogus_detail_url, "{}")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.catalogus_list_url, "{}")
        self.assertEqual(response.status_code, 201)

    @skip("This API is currently read-only.")
    def test_content_type_x_is_not_supported(self):
        """DSO: API-33 (content type application/x-www-form-urlencoded is not supported)"""
        # TODO: This guideline contradicts OAuth2 standards...
        response = self.client.patch(
            self.catalogus_detail_url,
            "{}",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 415)

        response = self.client.put(
            self.catalogus_detail_url,
            "{}",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 415)

        response = self.client.post(
            self.catalogus_list_url,
            "{}",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 415)


@skip("Not MVP")
class FilterSortSearchTests(APITestCase):
    """Section 2.6.6 of the DSO: API strategy"""

    def setUp(self):
        super().setUp()

        self.other_catalogus = Catalogus.objects.create(
            domein=self.catalogus.domein,
            rsin="999999999",
            contactpersoon_beheer_naam="John Doe",
        )

    def test_filter_on_single_field(self):
        """DSO: API-34 (filter on single field)"""
        # Filter on rsin
        response = self.client.get(
            "{}?rsin={}".format(self.catalogus_list_url, self.catalogus.rsin)
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["rsin"], self.catalogus.rsin)

        # Filter on domain
        response = self.client.get(
            "{}?domein={}".format(self.catalogus_list_url, self.catalogus.domein)
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)

    def test_filter_on_multiple_fields(self):
        """DSO: API-34 (filter on multiple fields)"""

        # Create an extra catalog to make sure it gets filtered out because of the different domain.
        Catalogus.objects.create(domein="XXXXX", rsin=self.catalogus.rsin)

        response = self.client.get(
            "{}?rsin={}&domein={}".format(
                self.catalogus_list_url, self.catalogus.rsin, self.catalogus.domein
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["rsin"], self.catalogus.rsin)

    def test_sort_query_param_is_called_sorteer(self):
        """DSO: API-35 (sort query param is called sorteer)"""
        # TODO: But why? expand is English...
        self.assertEqual(api_settings.ORDERING_PARAM, "sorteer")

    def test_sort_ascending(self):
        """DSO: API-35 (sort ascending)"""
        response = self.client.get("{}?sorteer=rsin".format(self.catalogus_list_url))
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["rsin"], self.catalogus.rsin)
        self.assertEqual(data["results"][1]["rsin"], self.other_catalogus.rsin)

    def test_sort_descending(self):
        """DSO: API-35 (sort descending)"""
        response = self.client.get("{}?sorteer=-rsin".format(self.catalogus_list_url))
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["rsin"], self.other_catalogus.rsin)
        self.assertEqual(data["results"][1]["rsin"], self.catalogus.rsin)

    def test_search_query_param_is_called_zoek(self):
        """DSO: API-36 (search query param is called zoek)"""
        # TODO: But why? expand is English...
        self.assertEqual(api_settings.SEARCH_PARAM, "zoek")

    def test_search_single_value(self):
        """DSO: API-36 (search single value)"""
        response = self.client.get(
            "{}?zoek={}".format(self.catalogus_list_url, self.catalogus.rsin)
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["rsin"], self.catalogus.rsin)

    def test_search_partial_value(self):
        """DSO: API-36 (search partial value)"""
        # TODO: This should probably not work but should only work when using wildcards.

        response = self.client.get("{}?zoek={}".format(self.catalogus_list_url, "Jo"))
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["rsin"], self.other_catalogus.rsin)

    def test_search_multiple_values(self):
        """DSO: API-36 (search multiple values)"""
        response = self.client.get(
            "{}?zoek={} {}".format(
                self.catalogus_list_url, "John", self.other_catalogus.rsin
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["rsin"], self.other_catalogus.rsin)

        # Another test to check whether it searching multiple values matches ALL search terms, and not just one.
        response = self.client.get(
            "{}?zoek={} {}".format(
                self.catalogus_list_url, "Jane", self.other_catalogus.rsin
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 0)

    def test_search_filter_and_sorting_combined(self):
        """Combination of DSO: API-34, API-35, API-36"""

        # There will be 4 catalogs now.
        catalogus_3 = Catalogus.objects.create(
            domein=self.catalogus.domein,
            rsin="111111111",
            contactpersoon_beheer_naam="Jane Doe",
        )
        catalogus_4 = Catalogus.objects.create(
            domein=self.catalogus.domein,
            rsin="222222222",
            contactpersoon_beheer_naam="Jane Doe",
        )

        # All query parameters will filter it down to 2, that are ordered.
        response = self.client.get(
            "{}?domein={}&zoek={}&sorteer={}".format(
                self.catalogus_list_url, self.catalogus.domein, "Jane", "rsin"
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["rsin"], catalogus_3.rsin)
        self.assertEqual(data["results"][1]["rsin"], catalogus_4.rsin)

    @expectedFailure
    def test_search_wildcard_star(self):
        """DSO: API-37 (search wildcard star)"""
        response = self.client.get(
            "{}?zoek={}*".format(
                self.catalogus_list_url, self.other_catalogus.rsin[0:4]
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)

    @expectedFailure
    def test_search_wildcard_question_mark(self):
        """DSO: API-37 (search wildcard question mark)"""
        response = self.client.get(
            "{}?zoek={}??????".format(
                self.catalogus_list_url, self.other_catalogus.rsin[0:4]
            )
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)


@skip("Not MVP")
class GeoTests(APITestCase):
    """Section 2.6.7 of the DSO: API strategy"""

    pass


@skip("Not MVP")
class PaginationTests(APITestCase):
    """Section 2.6.8 of the DSO: API strategy"""

    # TODO: This section of the DSO is very minimal and unclear.
    # TODO: Implicit, the word "pagina" is used to indicate the page but in contrast to "zoek", "expand", etc. it's
    # not specified.
    def setUp(self):
        super().setUp()

        # There will be 5 catalogs now.
        Catalogus.objects.create(domein=self.catalogus.domein, rsin="222222222")
        Catalogus.objects.create(domein=self.catalogus.domein, rsin="333333333")
        Catalogus.objects.create(domein=self.catalogus.domein, rsin="444444444")
        Catalogus.objects.create(domein=self.catalogus.domein, rsin="555555555")

        # Set page size to 2 items per page.
        # from openzaak.components.catalogi.api.utils.pagination import HALPagination
        # self._old_page_size = HALPagination.page_size
        # HALPagination.page_size = 2

    # def tearDown(self):
    #     from openzaak.components.catalogi.api.utils.pagination import HALPagination
    #     HALPagination.page_size = self._old_page_size

    @skip("Pagination disabled for now")
    def test_pagination_using_json_hal(self):
        """DSO: API-46 (pagination using JSON+HAL)"""
        response = self.client.get("{}?pagina=2".format(self.catalogus_list_url))
        self.assertEqual(response.status_code, 200)

        expected_headers = {
            "X-Total-Count": "5",
            "X-Pagination-Count": "3",
            "X-Pagination-Page": "2",
            "X-Pagination-Limit": "2",
        }

        for header, value in expected_headers.items():
            self.assertTrue(header in response)
            self.assertEqual(response[header], value, header)

        data = response.json()

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 2)

        self.assertTrue("_links" in data)

        expected_links = {
            "self": "http://testserver/api/v1/catalogussen/?pagina=2",
            "first": "http://testserver/api/v1/catalogussen/",
            "prev": "http://testserver/api/v1/catalogussen/",
            "next": "http://testserver/api/v1/catalogussen/?pagina=3",
            "last": "http://testserver/api/v1/catalogussen/?pagina=3",
        }

        links = data["_links"]
        for key, url in expected_links.items():
            self.assertTrue(key in links)
            self.assertEqual(links[key]["href"], url, key)


class CachingTests(APITestCase):
    """Section 2.6.9 of the DSO: API strategy"""

    @skip("This API does not implement caching yet.")
    def test_last_modified_response_header(self):
        """DSO: API-47 (last modified response header)"""
        pass

    @skip("This API does not implement caching yet.")
    def test_is_modified_since_request_header(self):
        """DSO: API-47 (is modified since request header)"""
        pass


class RateLimitTests(APITestCase):
    """Section 2.6.10 of the DSO: API strategy"""

    @skip("This API does not implement rate limits yet.")
    def test_rate_limit_response_header(self):
        """DSO: API-49 (rate limit response header)"""
        pass

    @skip("This API does not implement rate limits yet.")
    def test_limit_reached_status_code(self):
        """DSO: API-49 (limit reached status code)"""
        pass


@skip("Not MVP")
class ErrorHandlingTests(APITestCase):
    """Section 2.6.11 of the DSO: API strategy"""

    @skip("This API is currently read-only.")
    def test_standard_json_error_response_400(self):
        """DSO: API-50 (standard JSON error response 400)"""
        response = self.client.patch(
            self.catalogus_detail_url,
            data=json.dumps({"domein": "ABCDEFGH"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_standard_json_error_response_401(self):
        """DSO: API-50 (standard JSON error response 401)"""
        response = self.client.get(self.catalogus_detail_url)
        self.assertEqual(response.status_code, 401)

        data = response.json()

        self.assertDictEqual(
            data,
            {
                "type": "NotAuthenticated",
                "title": "Unauthorized",
                "status": 401,
                "detail": _("Authentication credentials were not provided."),
                "instance": self.catalogus_detail_url,
            },
        )

    def test_standard_json_error_response_404(self):
        """DSO: API-50 (standard JSON error response 404)"""
        non_existing_detail_url = reverse(
            "catalogus-detail", kwargs={"version": self.API_VERSION, "uuid": "dummy"}
        )

        response = self.client.get(non_existing_detail_url)
        self.assertEqual(response.status_code, 404)

        data = response.json()

        self.assertEqual(
            data,
            {
                "type": "Http404",
                "title": "Not Found",
                "status": 404,
                "detail": _("Not found."),
                "instance": non_existing_detail_url,
            },
        )


class DSOApi50Tests(APITestCase):
    """
    Test the error handling responses (API-50).
    """

    maxDiff = None
    factory = APIRequestFactory()

    def assertErrorResponse(self, view, expected_data: dict):
        _view = view.as_view()
        # method doesn't matter since we're using `dispatch`
        request = self.factory.get("/some/irrelevant/url")

        response = _view(request)

        expected_status = expected_data["status"]
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response["Content-Type"], "application/problem+json")

        # can't verify UUID...
        self.assertTrue(response.data["instance"].startswith("urn:uuid:"))
        del response.data["instance"]

        exc_class = view.exception.__class__.__name__
        expected_data["type"] = f"http://testserver/ref/fouten/{exc_class}/"
        self.assertEqual(response.data, expected_data)

    def test_400_error(self):
        self.assertErrorResponse(
            views.ValidationErrorView,
            {
                "code": "invalid",
                "title": "Invalid input.",
                "status": 400,
                "detail": "",
                "invalid_params": [
                    {
                        "name": "foo",
                        "code": "validation-error",
                        "reason": "Invalid data.",
                    }
                ],
            },
        )

    def test_401_error(self):
        self.assertErrorResponse(
            views.NotAuthenticatedView,
            {
                "code": "not_authenticated",
                "title": "Authenticatiegegevens zijn niet opgegeven.",
                "status": 401,
                "detail": "Authenticatiegegevens zijn niet opgegeven.",
            },
        )

    def test_403_error(self):
        self.assertErrorResponse(
            views.PermissionDeniedView,
            {
                "code": "permission_denied",
                "title": "Je hebt geen toestemming om deze actie uit te voeren.",
                "status": 403,
                "detail": "This action is not allowed",
            },
        )

    def test_404_error(self):
        self.assertErrorResponse(
            views.NotFoundView,
            {
                "code": "not_found",
                "title": "Niet gevonden.",
                "status": 404,
                "detail": "Some detail message",
            },
        )

    def test_405_error(self):
        self.assertErrorResponse(
            views.MethodNotAllowedView,
            {
                "code": "method_not_allowed",
                "title": 'Methode "{method}" niet toegestaan.',
                "status": 405,
                "detail": 'Methode "GET" niet toegestaan.',
            },
        )

    def test_406_error(self):
        self.assertErrorResponse(
            views.NotAcceptableView,
            {
                "code": "not_acceptable",
                "title": "Kan niet voldoen aan de opgegeven Accept header.",
                "status": 406,
                "detail": "Content negotation failed",
            },
        )

    def test_409_error(self):
        self.assertErrorResponse(
            views.ConflictView,
            {
                "code": "conflict",
                "title": "A conflict occurred",
                "status": 409,
                "detail": "The resource was updated, please retrieve it again",
            },
        )

    def test_410_error(self):
        self.assertErrorResponse(
            views.GoneView,
            {
                "code": "gone",
                "title": _("The resource is gone"),
                "status": 410,
                "detail": "The resource was destroyed",
            },
        )

    def test_412_error(self):
        self.assertErrorResponse(
            views.PreconditionFailedView,
            {
                "code": "precondition_failed",
                "title": _("Precondition failed"),
                "status": 412,
                "detail": "Something about CRS",
            },
        )

    def test_415_error(self):
        self.assertErrorResponse(
            views.UnsupportedMediaTypeView,
            {
                "code": "unsupported_media_type",
                "title": 'Ongeldige media type "{media_type}" in aanvraag.',
                "status": 415,
                "detail": "This media type is not supported",
            },
        )

    def test_429_error(self):
        self.assertErrorResponse(
            views.ThrottledView,
            {
                "code": "throttled",
                "title": "Aanvraag was verstikt.",
                "status": 429,
                "detail": "Too many requests",
            },
        )

    def test_500_error(self):
        self.assertErrorResponse(
            views.InternalServerErrorView,
            {
                "code": "error",
                "title": "Er is een serverfout opgetreden.",
                "status": 500,
                "detail": "Everything broke",
            },
        )
