# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
from unittest import skip

from django.test import tag

from rest_framework import status

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.tests.utils.e2e import ForeignSystemTestCase
from openzaak.utils.urls import reverse

from ..models import BesluitInformatieObject
from .factories import BesluitFactory


class ForeignDocumentTests(ForeignSystemTestCase):
    @tag("gh-2572")
    @skip("bio will allow external iots after #2618")
    def test_relate_foreign_document_reads_it_once_per_epoch(self):
        informatieobjecttype = self.create_foreign_informatieobjecttype()
        besluittype = BesluitTypeFactory.create(
            # informatieobjecttypen=[informatieobjecttype]
        )
        document = self.create_foreign_document(informatieobjecttype)
        besluit = BesluitFactory.create(besluittype=besluittype)

        response = self.client.post(
            reverse(BesluitInformatieObject),
            {"besluit": self.our_url(besluit), "informatieobject": document},
            headers={"host": self.our_host},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # a plain GET, then one revalidation after our own POST, as recorded against
        # the foreign system; on replay the matchers hold every request to that
        self.assertEqual(
            [
                (request.method, "If-None-Match" in request.headers)
                for request in self.cassette.requests
                if request.uri == document
                or request.uri.endswith("/objectinformatieobjecten")
            ],
            [("GET", False), ("POST", False), ("GET", True)],
        )
