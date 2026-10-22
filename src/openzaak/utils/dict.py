# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from collections.abc import Mapping


def get_by_path(d: Mapping[str, object], path: str, default: object = None) -> object:
    """
    Function to get a value from a nested dict at a specified path

    :param d: Dict to get the value from
    :type d: Mapping[str, object]
    :param path: Dotted path to get the value from
    :type path: str
    :param default: Default value to return
    :type default: object
    :return: The value found at the specified path
    :rtype: object
    """
    keys = path.split(".")
    value: object = d
    for key in keys:
        try:
            value = value[key]  # pyright: ignore[reportIndexIssue]
        except (KeyError, TypeError):
            return default
    return value
