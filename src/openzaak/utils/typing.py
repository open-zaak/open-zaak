from collections.abc import Mapping, Sequence

type JSONPrimitive = str | int | float | bool | None

type JSONValue = JSONPrimitive | JSONObject | Sequence[JSONValue]

type JSONObject = Mapping[str, JSONValue]
