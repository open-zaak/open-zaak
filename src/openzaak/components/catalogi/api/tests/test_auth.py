"""
Guarantee that the proper authorization amchinery is in place.
"""
import uuid
from unittest import skip

from rest_framework.test import APITestCase
from vng_api_common.tests import AuthCheckMixin, reverse


@skip('Current implementation is without authentication')
class ReadTests(AuthCheckMixin, APITestCase):

    def test_cannot_read_without_correct_scope(self):
        dummy_uuid = str(uuid.uuid4())
        urls = [
            # root
            reverse('catalogus-list'),
            reverse('catalogus-detail', kwargs={'uuid': dummy_uuid}),

            # nested one level
            reverse('zaaktype-list'),
            reverse('zaaktype-detail', kwargs={
                'uuid': dummy_uuid,
            }),
            reverse('informatieobjecttype-list'),
            reverse('informatieobjecttype-detail', kwargs={
                'uuid': dummy_uuid,
            }),
            reverse('besluittype-list'),
            reverse('besluittype-detail', kwargs={
                'uuid': dummy_uuid,
            }),

            # nested two levels
            reverse('statustype-list'),
            reverse('statustype-detail', kwargs={
                'uuid': dummy_uuid,
            }),
            reverse('eigenschap-list'),
            reverse('eigenschap-detail', kwargs={
                'uuid': dummy_uuid,
            }),
            reverse('roltype-list'),
            reverse('roltype-detail', kwargs={
                'uuid': dummy_uuid,
            }),

        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method='get')
