# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers

from collections.abc import Mapping, Sequence

type JSONPrimitive = str | int | float | bool | None

type JSONValue = JSONPrimitive | JSONObject | Sequence[JSONValue]

type JSONObject = Mapping[str, JSONValue]
