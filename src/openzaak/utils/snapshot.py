# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
"""
Request-scoped repeatable reads of external resources (#2572).

While handling one inbound request, each external URL is read at most once per
epoch. A new epoch starts when the scope is entered and at every unsafe outgoing
request; the first read of a URL in an epoch revalidates the stored
representation with ``If-None-Match``.

This module imports only the standard library, so it can be extracted without
changes. Keep it that way: the Django middleware and the wiring into
``AuthorizedRequestsLoader`` and the ``requests`` patch live elsewhere.

Laws, checked by ``tests/test_snapshot.py`` and, for the wiring,
``openzaak/tests/test_request_snapshot.py``:

0. Bounded staleness: ``fetch(t, u)`` returns the remote's representation of ``u``
   at some instant in the current epoch. A 304 counts as observing the remote.
1. One request per URL and epoch: within an epoch, fetches of ``u`` make one
   transport call that returns; one that raises doesn't count (law 4). It sends
   ``If-None-Match`` iff the store has an entry for ``u`` with an ETag.
2. Epoch boundaries: an epoch starts at scope entry and at every ``on_outgoing``
   of an unsafe method, which is called before sending, so whatever the outcome.
   Safe methods leave ``epoch`` and ``validated`` unchanged. ``is_safe`` agrees
   with the method ``requests`` sends (upper-cased), is sound (only methods
   registered as safe with IANA: calling a safe method unsafe merely costs a
   revalidation) and holds for RFC 9110's GET, HEAD, OPTIONS and TRACE.
3. Invalidation keeps the store: ``new_epoch`` leaves its entries unchanged.
4. Revalidation: ``NotModified`` returns the stored body and leaves the store
   unchanged, ``Ok`` replaces the entry, and an error drops the entry and the
   URL's validation and propagates, with no stale-if-error: the next fetch is a
   plain GET. Dropping the validation is redundant given the dropped entry; it
   keeps law 9 checkable locally.
5. Scope frame: outside a scope, ``fetch(t, u)`` is the body of
   ``t(u, if_none_match=None)``, nothing is stored and ``on_outgoing`` does
   nothing. Sibling scopes, e.g. in other threads, share no validation; with
   their own stores they share nothing.
6. No aliasing: mutating a returned value doesn't change later results, because
   the store keeps deep copies. Callers mutate what they get, and frozen types
   would break ``underscoreize`` and ``json.dumps``.
7. Representations share one entry: ``AuthorizedRequestsLoader.fetch_object(u)``
   is ``underscoreize`` of the raw body, and both make one call per epoch.
8. Bounded footprint: leaving a scope, also by an exception, restores the scope
   that was current before and releases a default store, and
   |store| <= |distinct URLs fetched with it|.
9. Validated implies stored: ``validated[u] == epoch`` implies
   ``store.get(u) is not None``, also for an entry without an ETag.

Consistency is per URL (repeatable read), not across URLs: without transactions
on the remote, ``u`` and ``v`` may be captured at different instants.
"""

import copy
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Protocol, assert_never

type JSON = None | bool | int | float | str | list[JSON] | dict[str, JSON]
type URL = str
type ETag = str
"""Opaque, as received; may carry ``W/``."""


@dataclass(frozen=True, slots=True)
class Entry:
    etag: ETag | None
    body: JSON
    """Raw (camelCase); never handed out, only copies."""


@dataclass(frozen=True, slots=True)
class Ok:
    etag: ETag | None
    body: JSON


@dataclass(frozen=True, slots=True)
class NotModified:
    pass


class Transport(Protocol):
    def __call__(
        self, url: URL, /, *, if_none_match: ETag | None
    ) -> Ok | NotModified: ...


class Store(Protocol):
    def get(self, url: URL, /) -> Entry | None: ...

    def put(self, url: URL, entry: Entry, /) -> None: ...

    def drop(self, url: URL, /) -> None:
        """Remove the entry for ``url``, if any."""
        ...


@dataclass(slots=True)
class Scope:
    store: Store
    epoch: int = 0
    validated: dict[URL, int] = field(default_factory=dict)
    """url -> epoch it was last validated in"""


_current: ContextVar[Scope | None] = ContextVar("snapshot_scope", default=None)


class DictStore(dict[URL, Entry]):
    def put(self, url: URL, entry: Entry, /) -> None:
        self[url] = entry

    def drop(self, url: URL, /) -> None:
        self.pop(url, None)


@contextmanager
def snapshot_scope(store: Store | None = None) -> Generator[Scope]:
    """
    Enter a scope, starting a new epoch. Without ``store`` the scope gets a fresh
    one that is released at exit.
    """
    # a new Scope validates nothing yet, even with a reused store (law 5);
    # ``is None``: an empty store is falsy
    scope = Scope(store=DictStore() if store is None else store)
    token = _current.set(scope)
    try:
        yield scope
    finally:
        _current.reset(token)


def current_scope() -> Scope | None:
    return _current.get()


def new_epoch(scope: Scope) -> None:
    scope.epoch += 1


def is_safe(method: str) -> bool:
    """
    Whether ``method`` is safe (RFC 9110 §9.2.1), as ``requests`` will send it:
    upper-cased.
    """
    return method.upper() in {"GET", "HEAD", "OPTIONS", "TRACE", "QUERY", "PRI"}


def on_outgoing(method: str) -> None:
    """
    Call before sending any outgoing request. An unsafe one starts a new epoch in
    the current scope, if any.
    """
    if not is_safe(method) and (scope := current_scope()):
        new_epoch(scope)


def fetch(transport: Transport, url: URL) -> JSON:
    """
    The raw body of ``url``; repeatable within an epoch when in a scope.

    Exceptions from ``transport`` propagate.
    """
    if_none_match: ETag | None = None
    entry = None
    scope = current_scope()
    if scope:
        entry = scope.store.get(url)
        if entry:
            if_none_match = entry.etag
            if scope.epoch == scope.validated.get(url):
                return copy.deepcopy(entry.body)

    try:
        response = transport(url, if_none_match=if_none_match)
    except Exception:
        if scope is not None:
            scope.store.drop(url)
            scope.validated.pop(url, None)
        raise

    match response:
        case Ok(etag=new_tag, body=json):
            # do somethigns with new_tag
            if scope:
                # the caller may mutate ``json``; the store keeps its own (law 6)
                scope.store.put(url, Entry(etag=new_tag, body=copy.deepcopy(json)))
                scope.validated[url] = scope.epoch
            return json
        case NotModified():
            assert entry
            assert scope
            scope.validated[url] = scope.epoch
            return copy.deepcopy(entry.body)
        case oops:
            assert_never(oops)
