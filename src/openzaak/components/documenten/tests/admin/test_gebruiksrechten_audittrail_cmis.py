# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid
from datetime import date, time

from django.test import override_settings, tag
from django.urls import reverse

from rest_framework import status
from vng_api_common import tests

from openzaak.utils.tests import AdminTestMixin, APICMISTestCase

from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory
from ..utils import get_operation_url


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenCMISAdminTests(AdminTestMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    def test_create_gebruiksrechten_is_forbidden_when_cmis_enabled(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create()
        informatieobject_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=informatieobject.uuid
        )
        add_url = reverse("admin:documenten_gebruiksrechten_add")
        data = {
            "uuid": uuid.uuid4(),
            "informatieobject": informatieobject_url,
            "omschrijving_voorwaarden": "desc",
            "startdatum_0": date(2019, 1, 1),
            "startdatum_1": time(10, 0, 0),
        }

        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_gebruiksrechten_is_forbidden_when_cmis_enabled(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = tests.reverse(eio)
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

        change_url = reverse(
            "admin:documenten_gebruiksrechten_change", args=(gebruiksrechten.uuid,)
        )

        data = {
            "uuid": gebruiksrechten.uuid,
            "omschrijving_voorwaarden": "new",
            "startdatum_0": date(2019, 1, 1),
            "startdatum_1": time(10, 0, 0),
        }

        response = self.client.post(change_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_gebruiksrechten_is_forbidden_when_cmis_enabled(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = tests.reverse(eio)
        gebruiksrechten = GebruiksrechtenCMISFactory(informatieobject=eio_url)

        delete_url = reverse(
            "admin:documenten_gebruiksrechten_delete", args=(gebruiksrechten.uuid,)
        )
        data = {"post": "yes"}

        response = self.client.post(delete_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
