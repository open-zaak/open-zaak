# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from typing import Iterable

from django import template

register = template.Library()


@register.filter
def all_true(iterable: Iterable, attribute: str) -> bool:
    """Template tag to perform `all()` for a specific attribute on a list

    Args:
        iterable (Iterable): the iterable to perform `all()` on
        attribute (str): the name of the attribute

    Returns:
        bool: True if all values of attribute in list are truthy, else False
    """
    return (
        all(iterable)
        if attribute is None
        else all(getattr(item, attribute) for item in iterable)
    )
