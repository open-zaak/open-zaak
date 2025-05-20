# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from typing import Optional

from vng_api_common.descriptors import GegevensGroepType


class GegevensGroepTypeWithReadOnlyFields(GegevensGroepType):
    """
    The GegevensGroepType __set__ method sets fields that were not passed to their default value.
    Zaak.opschorting has the field `eerdere_opschorting` as an internal read only value that should not be changeable.

    This subclass adds read only fields that will be set to their current value when __set__ is called.
    """

    def __init__(self, read_only: tuple = None, **kwargs):
        super().__init__(**kwargs)

        self.read_only = read_only

        read_only_fields_known = set(self.read_only).issubset(set(self.mapping.keys()))
        assert read_only_fields_known, (
            "The fields in 'read_only' must be a subset of the mapping keys"
        )

    def __set__(self, obj, value: Optional[dict]):
        if not value:
            value = {}

        for key in self.read_only:
            value[key] = getattr(obj, self.mapping[key].name)

        super().__set__(obj, value)
