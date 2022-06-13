# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import logging
from contextlib import ContextDecorator
from threading import local

from django.core import signals

import requests

logger = logging.getLogger(__name__)


__all__ = ["get_session", "use_connection_pool"]


class SessionHandler:
    def __init__(self):
        self._session = local()

    def get(self):
        if not hasattr(self._session, "num_blocks"):
            self._session.num_blocks = 0

        if hasattr(self._session, "session"):
            return self._session.session

        session = requests.Session()
        self._session.session = session
        return session

    def clear(self):
        if not hasattr(self._session, "session"):
            return

        # close the requests session
        self._session.session.close()

        # clear the thread local
        del self._session.session

        # reset the block count
        self._session.num_blocks = 0


sessions = SessionHandler()


def get_session():
    return sessions.get()


def close_old_session(**kwargs):
    sessions.clear()


class ConnectionPool(ContextDecorator):
    """
    Use and close a connection pool for requests in a given block.

    An instance can be used either as a decorator or as a context manager.

    The wrapped block will make use of a :class:`requests.Session` instance, which
    enables connection pooling. After the block is executed, the session is closed
    to prevent leaking resources.
    """

    def __enter__(self):
        # as long as the number of (nested) blocks doesn't reach zero, we can't close
        # the session (and thus the connection pool)
        session = get_session()
        sessions._session.num_blocks += 1
        return session

    def __exit__(self, exc_type, exc_value, traceback):
        # reduce the amount of tracked connection pool blocks, as we're exiting one
        sessions._session.num_blocks -= 1
        current_num_blocks = sessions._session.num_blocks
        logger.debug(
            "Exiting ConnectionPool block, there are %d blocks left",
            current_num_blocks,
        )

        if current_num_blocks <= 0:
            logger.debug("No more active connection pool blocks, closing the session.")
            sessions.clear()
        else:
            logger.debug("Active blocks left, not closing the session.")


def use_connection_pool(func=None):
    """
    Decorator or context manager to use a ``requests.Session`` connection pool.

    Obtain a session with ``connection_pooling.connections.get_session`` to make use of
    a connection pool. You can and should explicitly mark the block(s) where this pool
    applies. The session will be closed once the outer block exits.

    Usage:

        >>> @use_connection_pool
        ... def some_view(request):
        ...     session = get_session()
        ...     response = session.get(some_url)
    """
    # @use_connection_pool bare decorator syntax
    if callable(func):
        return ConnectionPool()(func)
    # @use_connection_pool() or context manager: with use_connection_pool(): ...
    else:
        return ConnectionPool()


# always clean up at the end of a request-response cycle by closing any open session
signals.request_finished.connect(close_old_session)
