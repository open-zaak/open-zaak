# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from rest_framework.request import Request

if TYPE_CHECKING:
    from openzaak.components.autorisaties.middleware import JWTAuth

type JSONPrimitive = str | int | float | bool | None

type JSONValue = JSONPrimitive | JSONObject | Sequence[JSONValue]

type JSONObject = Mapping[str, JSONValue]


class AuthorizedRequest(Request):
    jwt_auth: JWTAuth
