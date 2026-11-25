# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
"""
The laws of ``openzaak.utils.snapshot``, numbered as in its docstring. The wiring into the loader and ``requests`` is tested in
``openzaak/tests/test_request_snapshot.py``.
"""

import copy
import hashlib
import json
import subprocess
import sys
import threading
from collections.abc import Callable, Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Literal

from django.test import SimpleTestCase

from hypothesis import given, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)

from openzaak.utils import snapshot
from openzaak.utils.snapshot import (
    JSON,
    URL,
    Entry,
    ETag,
    NotModified,
    Ok,
    Scope,
    current_scope,
    fetch,
    is_safe,
    on_outgoing,
    snapshot_scope,
)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})  # RFC 9110
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# IANA HTTP Method Registry, by its "Safe" column
REGISTERED_SAFE = SAFE_METHODS | {"PRI", "PROPFIND", "QUERY", "REPORT", "SEARCH"}
REGISTERED_UNSAFE = UNSAFE_METHODS | {
    "ACL",
    "BASELINE-CONTROL",
    "BIND",
    "CHECKIN",
    "CHECKOUT",
    "CONNECT",
    "COPY",
    "LABEL",
    "LINK",
    "LOCK",
    "MERGE",
    "MKACTIVITY",
    "MKCALENDAR",
    "MKCOL",
    "MKREDIRECTREF",
    "MKWORKSPACE",
    "MOVE",
    "ORDERPATCH",
    "PROPPATCH",
    "REBIND",
    "UNBIND",
    "UNCHECKOUT",
    "UNLINK",
    "UNLOCK",
    "UPDATE",
    "UPDATEREDIRECTREF",
    "VERSION-CONTROL",
}

# few enough that fetches of the same URL collide
URLS: tuple[URL, ...] = (
    "https://drc.example.com/enkelvoudiginformatieobjecten/1",
    "https://drc.example.com/enkelvoudiginformatieobjecten/2",
    "https://ztc.example.com/zaaktypen/1",
)

type ETagStyle = Literal["strong", "weak"] | None


class RemoteError(Exception):
    """
    Stands in for ``FetchError``: the snapshot propagates whatever the transport
    raises.
    """


@dataclass(frozen=True, slots=True)
class Deleted:
    pass


type Version = Ok | Deleted


def make_version(body: JSON, style: ETagStyle) -> Ok:
    """A version whose ETag is derived from its body, like a content hash."""
    if style is None:
        return Ok(etag=None, body=body)
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    tag = f'"{digest[:8]}"'
    return Ok(etag=f"W/{tag}" if style == "weak" else tag, body=body)


def weak_match(a: ETag, b: ETag) -> bool:
    """Weak comparison, RFC 9110 §8.8.3.2."""
    return a.removeprefix("W/") == b.removeprefix("W/")


def vandalise(value: JSON) -> None:
    """Mutate every container in ``value`` in place."""
    match value:
        case dict():
            for child in list(value.values()):
                vandalise(child)
            value["vandalised"] = True
        case list():
            for child in list(value):
                vandalise(child)
            value.append("vandalised")
        case _:
            pass


class FakeRemote:
    """
    The remote's history per URL, and a ``Transport`` that serves its latest
    versions and records every call.
    """

    def __init__(self, initial: dict[URL, Version]) -> None:
        self.history: dict[URL, list[Version]] = {
            url: [version] for url, version in initial.items()
        }
        self.fail_next: set[URL] = set()
        self.calls: list[tuple[URL, ETag | None]] = []

    def respond(
        self, url: URL, if_none_match: ETag | None
    ) -> Ok | NotModified | RemoteError:
        """What a call would return now, without consuming ``fail_next``."""
        if url in self.fail_next:
            return RemoteError(f"500 {url}")
        match self.history[url][-1]:
            case Deleted():
                return RemoteError(f"404 {url}")
            case Ok(etag=str(etag)) if if_none_match is not None and weak_match(
                if_none_match, etag
            ):
                return NotModified()
            case Ok(etag=etag, body=body):
                # a fresh parse every time, like a real response
                return Ok(etag=etag, body=copy.deepcopy(body))

    def __call__(self, url: URL, /, *, if_none_match: ETag | None) -> Ok | NotModified:
        self.calls.append((url, if_none_match))
        response = self.respond(url, if_none_match)
        self.fail_next.discard(url)
        if isinstance(response, RemoteError):
            raise response
        return response


class DictStore(dict[URL, Entry]):
    """A ``Store`` the tests can inspect."""

    def put(self, url: URL, entry: Entry, /) -> None:
        self[url] = entry

    def drop(self, url: URL, /) -> None:
        self.pop(url, None)


def spellings(methods: Iterable[str]) -> st.SearchStrategy[str]:
    """``methods`` as callers may pass them; ``requests`` upper-cases them."""
    return st.sampled_from(sorted(methods)).flatmap(
        lambda method: st.sampled_from([method, method.lower(), method.title()])
    )


def json_containers(children: st.SearchStrategy[JSON]) -> st.SearchStrategy[JSON]:
    return st.lists(children, max_size=2) | st.dictionaries(
        st.text(max_size=2), children, max_size=2
    )


# no floats: NaN != NaN. No 0 or 1: they compare equal to False and True.
json_values: st.SearchStrategy[JSON] = st.recursive(
    st.none() | st.booleans() | st.integers(2, 4) | st.text(max_size=2),
    json_containers,
    max_leaves=6,
)
bodies: st.SearchStrategy[JSON] = st.dictionaries(
    st.text(max_size=2), json_values, max_size=3
)
etag_styles: st.SearchStrategy[ETagStyle] = st.sampled_from(["strong", "weak", None])
versions: st.SearchStrategy[Ok] = st.builds(make_version, bodies, etag_styles)
urls: st.SearchStrategy[URL] = st.sampled_from(URLS)


class SnapshotMachine(RuleBasedStateMachine):
    """
    The snapshot against a model of the store and of what was validated in the
    current epoch. ``FakeRemote`` is the environment: the model asks it what a
    call would return.
    """

    def __init__(self) -> None:
        super().__init__()
        self.remote = FakeRemote({})
        self.scopes = ExitStack()
        self.scope: Scope | None = None
        # outlives its scope, so the next one may reuse it
        self.store: DictStore | None = None

        self.model_store: dict[URL, Entry] = {}
        self.model_validated: set[URL] = set()
        self.fetched_into_store: set[URL] = set()
        # len(history[url]) when the current epoch started
        self.epoch_start: dict[URL, int] = {}
        # first result per URL in the current epoch
        self.seen: dict[URL, JSON] = {}

    @initialize(initial=st.tuples(*(versions for _ in URLS)))
    def init_remote(self, initial: tuple[Ok, ...]) -> None:
        self.remote = FakeRemote(dict(zip(URLS, initial, strict=True)))

    def teardown(self) -> None:
        self.scopes.close()

    def start_epoch(self) -> None:
        self.model_validated.clear()
        self.seen.clear()
        self.epoch_start = {url: len(h) for url, h in self.remote.history.items()}

    @precondition(lambda self: self.scope is None)
    @rule(reuse_store=st.booleans())
    def enter_scope(self, reuse_store: bool) -> None:
        # law 5 (scope frame): a reused store keeps its entries, but nothing counts
        # as validated
        if self.store is None or not reuse_store:
            self.store = DictStore()
            self.model_store = {}
            self.fetched_into_store = set()
        self.scope = self.scopes.enter_context(snapshot_scope(self.store))
        self.start_epoch()

    @precondition(lambda self: self.scope is not None)
    @rule()
    def exit_scope(self) -> None:
        self.scopes.close()
        self.scope = None

    @rule(url=urls, vandalise_result=st.booleans())
    def fetch(self, url: URL, vandalise_result: bool) -> None:
        in_scope = self.scope is not None
        if in_scope and url in self.model_validated:
            expected_calls = []
            response = None
        else:
            entry = self.model_store.get(url) if in_scope else None
            if_none_match = entry.etag if entry is not None else None
            expected_calls = [(url, if_none_match)]
            response = self.remote.respond(url, if_none_match)
        if in_scope:
            self.fetched_into_store.add(url)
        calls = len(self.remote.calls)

        result: JSON | RemoteError
        try:
            result = fetch(self.remote, url)
        except RemoteError as exc:
            result = exc

        # law 1 (one request per URL and epoch) in a scope, law 5 (scope frame) outside
        assert self.remote.calls[calls:] == expected_calls

        match response:
            case None | NotModified():
                # law 4 (revalidation): NotModified returns the stored body, store unchanged
                assert result == self.model_store[url].body, result
                self.model_validated.add(url)
            case RemoteError():
                # law 4 (revalidation): drop the entry and propagate
                assert isinstance(result, RemoteError), result
                if in_scope:
                    self.model_store.pop(url, None)
                    self.model_validated.discard(url)
                return
            case Ok(etag=etag, body=body):
                # law 4 (revalidation): Ok replaces the entry
                assert result == body, result
                if in_scope:
                    self.model_store[url] = Entry(etag=etag, body=copy.deepcopy(body))
                    self.model_validated.add(url)
        assert not isinstance(result, RemoteError)

        if in_scope:
            # law 0 (bounded staleness): a version the remote had in this epoch
            window = self.remote.history[url][self.epoch_start[url] - 1 :]
            assert any(isinstance(v, Ok) and v.body == result for v in window)
            # the goal: no two versions of one URL within an epoch
            assert self.seen.setdefault(url, copy.deepcopy(result)) == result

        if vandalise_result:
            # law 6 (no aliasing), checked by the next fetch and the invariants
            vandalise(result)

    def scope_state(self) -> tuple[int, dict[URL, int]] | None:
        if self.scope is None:
            return None
        return self.scope.epoch, dict(self.scope.validated)

    @rule(method=spellings(SAFE_METHODS))
    def safe_request(self, method: str) -> None:
        before = self.scope_state()
        on_outgoing(method)
        # law 2 (epoch boundaries): safe requests leave epoch and validated alone
        assert self.scope_state() == before

    @rule(method=spellings(UNSAFE_METHODS))
    def unsafe_request(self, method: str) -> None:
        # Whether the request itself succeeds is up to the ``requests`` hook,
        # which calls ``on_outgoing`` before sending; see test_request_snapshot.
        before = self.scope_state()
        on_outgoing(method)
        if self.scope is not None:
            assert before is not None
            # law 2 (epoch boundaries): a new epoch; law 3 (invalidation keeps the
            # store) via store_matches_model
            assert self.scope.epoch == before[0] + 1
            self.start_epoch()

    @rule(url=urls, version=versions)
    def remote_change(self, url: URL, version: Ok) -> None:
        self.remote.history[url].append(version)

    @rule(url=urls)
    def remote_delete(self, url: URL) -> None:
        self.remote.history[url].append(Deleted())

    @rule(url=urls)
    def remote_fail_next(self, url: URL) -> None:
        self.remote.fail_next.add(url)

    @invariant()
    def scope_is_current(self) -> None:
        assert current_scope() is self.scope

    @invariant()
    def store_matches_model(self) -> None:
        # law 3 (invalidation keeps the store), law 4 (revalidation), and law 6
        # (no aliasing) for what the store holds
        if self.store is not None:
            assert dict(self.store) == self.model_store

    @invariant()
    def validated_matches_model(self) -> None:
        if self.scope is not None:
            validated = {
                url
                for url, epoch in self.scope.validated.items()
                if epoch == self.scope.epoch
            }
            assert validated == self.model_validated

    @invariant()
    def bounded_footprint(self) -> None:
        # law 8 (bounded footprint)
        if self.store is not None:
            assert self.store.keys() <= self.fetched_into_store

    @invariant()
    def validated_implies_stored(self) -> None:
        # law 9 (validated implies stored)
        if self.scope is not None:
            for url, epoch in self.scope.validated.items():
                if epoch == self.scope.epoch:
                    assert self.scope.store.get(url) is not None, url


class SnapshotMachineTests(SnapshotMachine.TestCase):
    """Named here, so ``manage.py test --parallel`` can pickle it."""


class SnapshotTests(SimpleTestCase):
    def assert_is_safe_laws(self, method: str) -> None:
        # as ``requests`` will send it
        self.assertEqual(is_safe(method), is_safe(method.upper()))
        # sound, for law 2 (epoch boundaries): calling a safe method unsafe only costs a
        # revalidation, but the converse would skip a new epoch
        if is_safe(method):
            self.assertIn(method.upper(), REGISTERED_SAFE)
        # complete for RFC 9110, so our own GETs don't start epochs
        if method.upper() in SAFE_METHODS:
            self.assertTrue(is_safe(method))

    def test_is_safe_for_registered_methods(self):
        for registered in sorted(REGISTERED_SAFE | REGISTERED_UNSAFE):
            for method in (registered, registered.lower(), registered.title()):
                with self.subTest(method=method):
                    self.assert_is_safe_laws(method)

    @given(st.text(max_size=8))
    def test_is_safe(self, method: str):
        self.assert_is_safe_laws(method)

    @given(version=versions)
    def test_results_dont_alias(self, version: Ok):
        """Law 6 (no aliasing) on each path: Ok, validated in this epoch, NotModified."""
        url = URLS[0]
        remote = FakeRemote({url: version})

        with snapshot_scope():
            for start_epoch in (False, False, True, False):
                if start_epoch:
                    on_outgoing("POST")
                result = fetch(remote, url)
                self.assertEqual(result, version.body)
                vandalise(result)

        # law 1 (one request per URL and epoch) with the default store
        self.assertEqual(remote.calls, [(url, None), (url, version.etag)])

    def test_scope_exit(self):
        """Law 8 (bounded footprint): the scope is left on exit, also on an exception."""
        with snapshot_scope() as scope:
            self.assertIs(current_scope(), scope)
        self.assertIsNone(current_scope())

        with self.assertRaises(RemoteError), snapshot_scope():
            raise RemoteError
        self.assertIsNone(current_scope())

    def test_sibling_scopes_in_threads(self):
        """
        Law 5 (scope frame): one thread's unsafe request doesn't start an epoch in another
        thread's scope, and their first fetches don't see each other.
        """
        url = URLS[0]
        v1, v2 = make_version({"v": 2}, "strong"), make_version({"v": 3}, "strong")
        remote = FakeRemote({url: v1})
        in_flight = threading.Barrier(2, timeout=5)
        step = threading.Barrier(2, timeout=5)
        calls: dict[str, list[ETag | None]] = {"a": [], "b": []}
        results: dict[str, list[JSON]] = {"a": [], "b": []}
        errors: list[BaseException] = []

        def transport(url: URL, /, *, if_none_match: ETag | None) -> Ok | NotModified:
            name = threading.current_thread().name
            calls[name].append(if_none_match)
            if len(calls[name]) == 1:
                in_flight.wait()  # both first fetches are in flight at once
            return remote(url, if_none_match=if_none_match)

        def a() -> None:
            with snapshot_scope():
                results["a"].append(fetch(transport, url))
                step.wait()
                step.wait()  # meanwhile b makes an unsafe request, the remote changes
                results["a"].append(fetch(transport, url))

        def b() -> None:
            with snapshot_scope():
                results["b"].append(fetch(transport, url))
                step.wait()
                on_outgoing("POST")
                remote.history[url].append(v2)
                step.wait()
                results["b"].append(fetch(transport, url))

        def reporting(target: Callable[[], None]) -> Callable[[], None]:
            def run() -> None:
                try:
                    target()
                except BaseException as exc:
                    errors.append(exc)
                    in_flight.abort()
                    step.abort()

            return run

        threads = [
            threading.Thread(target=reporting(target), name=name)
            for name, target in (("a", a), ("b", b))
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        if errors:
            raise errors[0]

        self.assertEqual(results["a"], [v1.body, v1.body])
        self.assertEqual(calls["a"], [None])
        self.assertEqual(results["b"], [v1.body, v2.body])
        self.assertEqual(calls["b"], [None, v1.etag])

    def test_imports_only_the_standard_library(self):
        """So it can be extracted to ape_pie or zgw-consumers as is."""
        code = "\n".join(
            [
                "import importlib.util, sys",
                "before = set(sys.modules)",
                f"spec = importlib.util.spec_from_file_location('snapshot', {snapshot.__file__!r})",
                "module = importlib.util.module_from_spec(spec)",
                "sys.modules['snapshot'] = module",
                "spec.loader.exec_module(module)",
                "new = {name.partition('.')[0] for name in set(sys.modules) - before}",
                "print(sorted(new - sys.stdlib_module_names - {'snapshot'}))",
            ]
        )
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "[]")
