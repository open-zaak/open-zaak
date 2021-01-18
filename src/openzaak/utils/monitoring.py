# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import collections.abc
import re

from inflection import camelize


def nested_update(mapping, keys, value="(filtered)"):
    for i, k in enumerate(keys):
        current = mapping.get(k, None)
        if not current:
            break

        if isinstance(current, collections.abc.Mapping):
            mapping[k] = nested_update(current, keys[i + 1 :])
        elif isinstance(current, list):
            mapping[k] = [nested_update(item, keys[i + 1 :]) for item in current]
        else:
            mapping[k] = value
    return mapping


def filter_sensitive_data(event, hint):
    # Filter these values, so they do not show up in Sentry
    for key in ["inp_bsn", "inp_a_nummer", "anp_identificatie"]:
        event = nested_update(
            event, ["request", "data", "betrokkene_identificatie", key]
        )
        event = nested_update(
            event,
            ["exception", "values", "stacktrace", "frames", "vars", "group_data", key],
        )

        prefix = "betrokkeneIdentificatie__natuurlijkPersoon"

        camelized = camelize(key, False)
        if key == "inp_a_nummer":
            camelized = "inpA_nummer"

        pattern = f"({prefix}__{camelized}=)([^&]*)(&|$)"

        if "querystring" in event.get("request", {}):
            event["request"]["querystring"] = re.sub(
                pattern, r"\g<1>(filtered)\g<3>", event["request"]["querystring"]
            )
    return event
