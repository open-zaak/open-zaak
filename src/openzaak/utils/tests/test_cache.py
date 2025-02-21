# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import sleep

from django.test import SimpleTestCase, tag

import requests
from furl import furl

from openzaak.tests.utils import require_cmis

from ..cache import _requests_cache_enabled, run_in_process_with_caching

TEST_SERVER_URL = furl("http://localhost:8888/")


class TestRequestHandler(BaseHTTPRequestHandler):
    """
    `requests_mock.Mocker` cannot be used to perform assertions to the request_history when
    performing requests from different processes, so instead we spin up a temporary
    HTTP server and store the requests to make assertions on them
    """

    request_log = []  # Stores all received requests for verification

    def do_GET(self):
        """Handles GET requests."""
        self.__class__.request_log.append(self.path)  # Log request
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Test Response")


def start_test_server():
    """Starts a simple HTTP server on localhost:8888"""
    server = HTTPServer(("localhost", 8888), TestRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class RequestsCacheTests(SimpleTestCase):
    def setUp(self):
        super().setUp()

        server = start_test_server()

        # clear the logs
        TestRequestHandler.request_log = []
        self.addCleanup(server.shutdown)

    @tag("gh-1907")
    def test_request_cache_applies_globally_if_run_in_same_process(self):
        """
        When performing requests within the `_requests_cache_enabled` context manager
        in the same process, requests will be cached globally while that context manager is active
        """

        def cached_function():
            with _requests_cache_enabled():
                sleep(0.2)
                requests.get((TEST_SERVER_URL / "inside-context-manager").url)
                requests.get((TEST_SERVER_URL / "inside-context-manager").url)

                from vng_api_common.client import Client

                client = Client(base_url=TEST_SERVER_URL.url)

                client.get("/custom-client-inside-context-manager")
                client.get("/custom-client-inside-context-manager")

        def perform_requests():
            # Make two requests, these should not be patched
            sleep(0.1)
            requests.get((TEST_SERVER_URL / "not-inside-context-manager").url)
            requests.get((TEST_SERVER_URL / "not-inside-context-manager").url)

            from vng_api_common.client import Client

            client = Client(base_url=TEST_SERVER_URL.url)
            client.get("/custom-client-not-inside-context-manager")
            client.get("/custom-client-not-inside-context-manager")

        cached_thread = threading.Thread(target=cached_function)
        non_cached_thread = threading.Thread(target=perform_requests)

        # start and wait for threads to finish
        cached_thread.start()
        non_cached_thread.start()
        cached_thread.join()
        non_cached_thread.join()

        self.assertEqual(len(TestRequestHandler.request_log), 4)

        request1, request2, request3, request4 = TestRequestHandler.request_log
        self.assertEqual(request1, "/not-inside-context-manager")
        self.assertEqual(request2, "/custom-client-not-inside-context-manager")
        self.assertEqual(request3, "/inside-context-manager")
        self.assertEqual(request4, "/custom-client-inside-context-manager")

    # Unfortunately this test cannot be run in parallel, because parallel processes
    # with daemon=True cannot spawn child processes themselves, so we run it as part of
    # the CMIS tests, which are not run in parallel
    @require_cmis
    @tag("gh-1907")
    def test_request_cache_does_not_apply_globally_if_run_in_separate_process(self):
        """
        When performing requests within the `_requests_cache_enabled` context manager
        in a different process, requests should not be cached globally while this different
        process is active. This is the preferred way of using requests-cache
        """

        def cached_function():
            def perform_requests():
                sleep(0.2)
                requests.get((TEST_SERVER_URL / "cached").url)
                requests.get((TEST_SERVER_URL / "cached").url)

                from vng_api_common.client import Client

                client = Client(base_url=TEST_SERVER_URL.url)
                client.get("/custom-client-cached")
                client.get("/custom-client-cached")

            run_in_process_with_caching(perform_requests)

        def perform_requests():
            # Make two requests, these should not be patched
            sleep(0.1)
            requests.get((TEST_SERVER_URL / "not-cached").url)
            requests.get((TEST_SERVER_URL / "not-cached").url)

            from vng_api_common.client import Client

            client = Client(base_url=TEST_SERVER_URL.url)
            client.get("/custom-client-not-cached")
            client.get("/custom-client-not-cached")

        cached_thread = threading.Thread(target=cached_function)
        non_cached_thread = threading.Thread(target=perform_requests)

        # start and wait for threads to finish
        cached_thread.start()
        non_cached_thread.start()
        cached_thread.join()
        non_cached_thread.join()

        self.assertEqual(len(TestRequestHandler.request_log), 6)

        request1, request2, request3, request4, request5, request6 = (
            TestRequestHandler.request_log
        )

        self.assertEqual(request1, "/not-cached")
        self.assertEqual(request2, "/not-cached")
        self.assertEqual(request3, "/custom-client-not-cached")
        self.assertEqual(request4, "/custom-client-not-cached")
        self.assertEqual(request5, "/cached")
        self.assertEqual(request6, "/custom-client-cached")

    # Unfortunately this test cannot be run in parallel, because parallel processes
    # with daemon=True cannot spawn child processes themselves, so we run it as part of
    # the CMIS tests, which are not run in parallel
    @require_cmis
    @tag("gh-1907")
    def test_errors_in_parallel_process_are_raised(self):
        """
        Assert that any exceptions raised within a function that is being run in a separate
        process bubble up
        """

        def function_that_raises_exception():
            raise Exception

        with self.assertRaises(Exception):
            run_in_process_with_caching(function_that_raises_exception)
