from unittest.mock import patch


class BesluitInformatieObjectSyncMixin:

    def setUp(self):
        super().setUp()

        patcher_sync_create = patch('openzaak.components.besluiten.sync.signals.sync_create_bio')
        self.mocked_sync_create_bio = patcher_sync_create.start()
        self.addCleanup(patcher_sync_create.stop)

        patcher_sync_delete = patch('openzaak.components.besluiten.sync.signals.sync_delete_bio')
        self.mocked_sync_delete_bio = patcher_sync_delete.start()
        self.addCleanup(patcher_sync_delete.stop)


class BesluitSyncMixin:

    def setUp(self):
        super().setUp()

        patcher_sync_create = patch('openzaak.components.besluiten.sync.signals.sync_create_besluit')
        self.mocked_sync_create_besluit = patcher_sync_create.start()
        self.addCleanup(patcher_sync_create.stop)

        patcher_sync_delete = patch('openzaak.components.besluiten.sync.signals.sync_delete_besluit')
        self.mocked_sync_delete_besluit = patcher_sync_delete.start()
        self.addCleanup(patcher_sync_delete.stop)


class MockSyncMixin(BesluitSyncMixin, BesluitInformatieObjectSyncMixin):
    pass
