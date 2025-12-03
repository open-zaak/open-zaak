from django.utils.functional import LazyObject

from ...storage import documenten_storage


class AzureBlobStorageMixin:
    """
    Mixin to make sure the underlying Documenten storage backend can be overridden
    with `@override_settings`
    """

    def setUp(self):
        super().setUp()

        assert isinstance(documenten_storage, LazyObject)

        # TODO find cleaner solution
        documenten_storage._wrapped = None  # force reload
        documenten_storage._setup()
