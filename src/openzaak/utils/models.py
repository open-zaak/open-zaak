# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
import copy


def clone_object(instance):
    cloned = copy.deepcopy(instance)  # don't alter original instance
    cloned.pk = None
    cloned._state.adding = True
    try:
        delattr(cloned, "_prefetched_objects_cache")
    except AttributeError:
        pass
    return cloned
