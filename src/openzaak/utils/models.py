# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import contextlib
import copy


def clone_object(instance):
    cloned = copy.deepcopy(instance)  # don't alter original instance
    cloned.pk = None
    cloned._state.adding = True
    with contextlib.suppress(AttributeError):
        delattr(cloned, "_prefetched_objects_cache")
    return cloned
