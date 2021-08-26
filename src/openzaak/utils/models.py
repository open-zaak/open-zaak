import copy


def clone_object(instance):
    cloned = copy.copy(instance) # don't alter original instance
    cloned.pk = None
    try:
        delattr(cloned, '_prefetched_objects_cache')
    except AttributeError:
        pass
    return cloned
