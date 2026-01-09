# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from typing import Any


def get_by_path(d: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Function to get a value from a nested dict at a specified path

    :param d: Dict to get the value from
    :type d: dict[str, Any]
    :param path: Dotted path to get the value from
    :type path: str
    :param default: Default value to return
    :type default: Any
    :return: The value found at the specified path
    :rtype: Any
    """
    keys = path.split(".")
    for key in keys:
        try:
            d = d[key]
        except (KeyError, TypeError):
            return default
    return d
