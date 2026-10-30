# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from django.test import tag

from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.tests.utils.e2e import ForeignSystemTestCase

from ..models import BesluitInformatieObject
from .factories import BesluitFactory


class ForeignDocumentTests(ForeignSystemTestCase):
    @tag("gh-2572")
    def test_relate_foreign_document_reads_it_once_per_epoch(self):
        catalogus = self.create_foreign_catalogus()
        informatieobjecttype = self.create_foreign_informatieobjecttype(catalogus)
        besluittype = self.create_foreign_besluittype(catalogus, informatieobjecttype)
        document = self.create_foreign_document(informatieobjecttype)
        besluit = BesluitFactory.create(besluittype=besluittype)

        with self.sent_requests() as sent:
            response = self.client.post(
                reverse(BesluitInformatieObject),
                {"besluit": self.our_url(besluit), "informatieobject": document},
                headers={"host": self.our_host},
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # a plain GET, then one revalidation after our own POST
        self.assertEqual(
            [
                (request.method, "If-None-Match" in request.headers)
                for request in sent
                if request.url == document or request.method != "GET"
            ],
            [("GET", False), ("POST", False), ("GET", True)],
        )
