# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
"""
The wiring of ``openzaak.utils.snapshot`` into ``AuthorizedRequestsLoader`` and
the ``requests`` patch; laws are numbered as in ``openzaak.utils.snapshot``.
"""

from contextlib import suppress

from django.test import SimpleTestCase

import requests
import requests_mock
from ape_pie import APIClient
from djangorestframework_camel_case.util import underscoreize
from hypothesis import given, settings, strategies as st
from hypothesis.extra.django import TestCase as HypothesisTestCase

from openzaak.loaders import AuthorizedRequestsLoader
from openzaak.utils.snapshot import JSON, snapshot_scope
from openzaak.utils.tests.test_snapshot import vandalise

API_ROOT = "https://drc.example.com/api/v1/"
URL = f"{API_ROOT}enkelvoudiginformatieobjecten/1"

camel_keys = st.text(alphabet="aBc_", min_size=1, max_size=4)


def camel_containers(children: st.SearchStrategy[JSON]) -> st.SearchStrategy[JSON]:
    return st.lists(children, max_size=2) | st.dictionaries(
        camel_keys, children, max_size=2
    )


camel_values: st.SearchStrategy[JSON] = st.recursive(
    st.none() | st.text(max_size=2), camel_containers, max_leaves=6
)
camel_bodies: st.SearchStrategy[JSON] = st.dictionaries(
    camel_keys, camel_values, max_size=3
)


class LoaderSnapshotTests(HypothesisTestCase):
    # database queries and mocked HTTP have uneven timings
    @settings(deadline=None)
    @given(body=camel_bodies, raw_reads=st.lists(st.booleans(), min_size=1, max_size=4))
    def test_representations_share_one_entry(self, body: JSON, raw_reads: list[bool]):
        """Law 7 (representations share one entry), law 6 (no aliasing) for both."""
        with requests_mock.Mocker() as m, snapshot_scope():
            m.get(URL, json=body, headers={"ETag": '"1"'})
            for raw in raw_reads:
                result = AuthorizedRequestsLoader.fetch_object(
                    URL, do_underscoreize=not raw
                )
                self.assertEqual(result, body if raw else underscoreize(body))
                vandalise(result)

        self.assertEqual(m.call_count, 1)

    @settings(deadline=None)
    @given(body=camel_bodies, reads=st.integers(1, 3))
    def test_outside_a_scope(self, body: JSON, reads: int):
        """Law 5 (scope frame): every read is a plain GET, as before."""
        with requests_mock.Mocker() as m:
            m.get(URL, json=body, headers={"ETag": '"1"'})
            for _ in range(reads):
                AuthorizedRequestsLoader.fetch_object(URL)

        self.assertEqual(m.call_count, reads)
        for request in m.request_history:
            self.assertNotIn("If-None-Match", request.headers)


class OutgoingRequestEpochTests(SimpleTestCase):
    """Law 2 (epoch boundaries) at the ``Session.request`` patch in ``openzaak.setup``."""

    responses = {
        "succeeds": {"status_code": 201},
        "fails": {"status_code": 500},
        "raises": {"exc": requests.ConnectionError},
    }

    def test_unsafe_request_starts_an_epoch(self):
        for method in ("POST", "PUT", "PATCH", "DELETE", "post"):
            for outcome, response in self.responses.items():
                with (
                    self.subTest(method=method, outcome=outcome),
                    requests_mock.Mocker() as m,
                    snapshot_scope() as scope,
                ):
                    m.register_uri(method.upper(), URL, **response)
                    epoch = scope.epoch

                    with suppress(requests.ConnectionError):
                        requests.request(method, URL)

                    self.assertEqual(scope.epoch, epoch + 1)

    def test_safe_request_keeps_the_epoch(self):
        for method in ("GET", "HEAD", "OPTIONS", "get"):
            with (
                self.subTest(method=method),
                requests_mock.Mocker() as m,
                snapshot_scope() as scope,
            ):
                m.register_uri(method.upper(), URL, json={})
                epoch, validated = scope.epoch, dict(scope.validated)

                requests.request(method, URL)

                self.assertEqual((scope.epoch, scope.validated), (epoch, validated))

    def test_zgw_consumers_clients_go_through_the_hook(self):
        with requests_mock.Mocker() as m, snapshot_scope() as scope:
            m.post(f"{API_ROOT}objectinformatieobjecten", status_code=201, json={})
            epoch = scope.epoch

            with APIClient(API_ROOT) as client:
                client.post("objectinformatieobjecten")

            self.assertEqual(scope.epoch, epoch + 1)

    def test_unsafe_request_outside_a_scope(self):
        """Law 5 (scope frame): Celery and management commands send unsafe requests too."""
        with requests_mock.Mocker() as m:
            m.post(URL, status_code=201)

            requests.post(URL)

        self.assertEqual(m.call_count, 1)
