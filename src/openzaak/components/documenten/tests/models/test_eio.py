# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase, override_settings, tag

import requests_mock
from privates.test import temp_private_root
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import MockSchemasMixin

from ..factories import EnkelvoudigInformatieObjectFactory
from ..utils import get_informatieobjecttype_response


@tag("external-urls")
@temp_private_root()
@override_settings(ALLOWED_HOSTS=["testserver"])
class EIOTestCase(MockSchemasMixin, TestCase):
    mocker_attr = "requests_mock"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

    def setUp(self):
        self.requests_mock = requests_mock.Mocker()
        self.requests_mock.start()
        self.addCleanup(self.requests_mock.stop)

        super().setUp()

    def test_update_iot_external_to_local(self):
        local_iot = InformatieObjectTypeFactory.create()
        external_catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        external_informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        self.requests_mock.get(
            external_informatieobjecttype,
            json=get_informatieobjecttype_response(
                external_catalogus, external_informatieobjecttype
            ),
        )
        self.requests_mock.get(
            external_catalogus,
            json=get_informatieobjecttype_response(
                external_catalogus, external_informatieobjecttype
            ),
        )
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=external_informatieobjecttype,
        )

        eio.informatieobjecttype = local_iot
        eio.save()

        eio.refresh_from_db()
        self.assertIsNone(eio._informatieobjecttype_url)
        self.assertEqual(eio._informatieobjecttype, local_iot)
        self.assertEqual(eio.informatieobjecttype, local_iot)

    def test_update_iot_local_to_external(self):
        local_iot = InformatieObjectTypeFactory.create(concept=False)
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=local_iot,
        )
        external_catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        external_informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        self.requests_mock.get(
            external_informatieobjecttype,
            json=get_informatieobjecttype_response(
                external_catalogus, external_informatieobjecttype
            ),
        )
        self.requests_mock.get(
            external_catalogus,
            json=get_informatieobjecttype_response(
                external_catalogus, external_informatieobjecttype
            ),
        )

        eio.informatieobjecttype = external_informatieobjecttype
        eio.save()

        eio.refresh_from_db()
        self.assertEqual(eio._informatieobjecttype_url, external_informatieobjecttype)
        self.assertIsNone(eio._informatieobjecttype)
        self.assertEqual(eio.informatieobjecttype, external_informatieobjecttype)
