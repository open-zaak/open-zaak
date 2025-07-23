# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from copy import deepcopy

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.tests import reverse
from vng_api_common.utils import get_uuid_from_path

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory


class AuditTrailTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def _create_besluit(self, **headers):
        url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        besluit_data = {
            "verantwoordelijkeOrganisatie": "000000000",
            "besluittype": f"http://testserver{besluittype_url}",
            "datum": "2019-04-25",
            "ingangsdatum": "2019-04-26",
            "vervaldatum": "2019-04-28",
            "identificatie": "123123",
        }
        response = self.client.post(url, besluit_data, **headers)

        return response.data

    def test_create_besluit_audittrail(self):
        besluit_response = self._create_besluit()

        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_response["url"])
        self.assertEqual(audittrails.count(), 1)

        # Verify that the audittrail for the Besluit creation contains the correct
        # information
        besluit_create_audittrail = audittrails.get()
        self.assertEqual(besluit_create_audittrail.bron, "BRC")
        self.assertEqual(besluit_create_audittrail.actie, "create")
        self.assertEqual(besluit_create_audittrail.resultaat, 201)
        self.assertEqual(besluit_create_audittrail.oud, None)
        self.assertEqual(besluit_create_audittrail.nieuw, besluit_response)

    def test_update_besluit_audittrails(self):
        besluit_data = self._create_besluit()

        modified_data = deepcopy(besluit_data)
        url = modified_data.pop("url")
        modified_data["toelichting"] = "aangepast"

        response = self.client.put(url, modified_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        besluit_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_response["url"])
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the Besluit update contains the correct
        # information
        besluit_update_audittrail = audittrails[1]
        self.assertEqual(besluit_update_audittrail.bron, "BRC")
        self.assertEqual(besluit_update_audittrail.actie, "update")
        self.assertEqual(besluit_update_audittrail.resultaat, 200)
        self.assertEqual(besluit_update_audittrail.oud, besluit_data)
        self.assertEqual(besluit_update_audittrail.nieuw, besluit_response)

    def test_partial_update_besluit_audittrails(self):
        besluit_data = self._create_besluit()

        response = self.client.patch(besluit_data["url"], {"toelichting": "aangepast"})
        besluit_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_response["url"])
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the Besluit partial_update contains the
        # correct information
        besluit_update_audittrail = audittrails[1]
        self.assertEqual(besluit_update_audittrail.bron, "BRC")
        self.assertEqual(besluit_update_audittrail.actie, "partial_update")
        self.assertEqual(besluit_update_audittrail.resultaat, 200)
        self.assertEqual(besluit_update_audittrail.oud, besluit_data)
        self.assertEqual(besluit_update_audittrail.nieuw, besluit_response)

    def test_create_besluitinformatieobject_audittrail(self):
        besluit_data = self._create_besluit()

        besluit = Besluit.objects.get()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        besluit.besluittype.informatieobjecttypen.add(io.informatieobjecttype)
        url = reverse(BesluitInformatieObject)

        response = self.client.post(
            url,
            {
                "besluit": besluit_data["url"],
                "informatieobject": f"http://testserver{io_url}",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        besluitinformatieobject_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_data["url"])
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the BesluitInformatieObject creation
        # contains the correct information
        bio_create_audittrail = audittrails[1]
        self.assertEqual(bio_create_audittrail.bron, "BRC")
        self.assertEqual(bio_create_audittrail.actie, "create")
        self.assertEqual(bio_create_audittrail.resultaat, 201)
        self.assertEqual(bio_create_audittrail.oud, None)
        self.assertEqual(bio_create_audittrail.nieuw, besluitinformatieobject_response)

    def test_verwerk_besluit_audittrails(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        besluittype.informatieobjecttypen.add(informatieobjecttype)

        informatieobject_1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_1 = reverse(informatieobject_1)

        informatieobject_2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=informatieobjecttype
        )
        informatieobject_url_2 = reverse(informatieobject_2)

        url = reverse("verwerkbesluit-list")

        data = {
            "besluit": {
                "verantwoordelijkeOrganisatie": "000000000",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2019-04-25",
                "ingangsdatum": "2019-04-26",
                "vervaldatum": "2019-04-28",
                "identificatie": "123123",
            },
            "besluitinformatieobjecten": [
                {"informatieobject": f"http://testserver{informatieobject_url_1}"},
                {"informatieobject": f"http://testserver{informatieobject_url_2}"},
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 201)

        self.assertEqual(AuditTrail.objects.count(), 3)

        besluit_audittrail = AuditTrail.objects.get(
            hoofd_object=response.data["besluit"]["url"]
        )

        self.assertEqual(besluit_audittrail.bron, "BRC")
        self.assertEqual(besluit_audittrail.actie, "create")
        self.assertEqual(besluit_audittrail.resource, "besluit")
        self.assertEqual(besluit_audittrail.oud, None)
        self.assertEqual(besluit_audittrail.nieuw, response.data["besluit"])

        for trail in AuditTrail.objects.filter(
            nieuw__in=response.data["besluitinformatieobjecten"]
        ):
            self.assertEqual(trail.bron, "BRC")
            self.assertEqual(trail.actie, "create")
            self.assertEqual(trail.resource, "besluitinformatieobject")
            self.assertEqual(trail.oud, None)

    def test_delete_besluit_cascade_audittrails(self):
        besluit_data = self._create_besluit()

        # Delete the Besluit
        response = self.client.delete(besluit_data["url"])

        self.assertEqual(response.status_code, 204)
        # Verify that deleting the Besluit deletes all related AuditTrails
        audittrails = AuditTrail.objects.filter(hoofd_object=besluit_data["url"])
        self.assertFalse(audittrails.exists())

    def test_audittrail_applicatie_information(self):
        besluit_response = self._create_besluit()

        audittrail = AuditTrail.objects.filter(
            hoofd_object=besluit_response["url"]
        ).get()

        # Verify that the application id stored in the AuditTrail matches
        # the id of the Application used for the request
        self.assertEqual(audittrail.applicatie_id, str(self.applicatie.uuid))

        # Verify that the application representation stored in the AuditTrail
        # matches the label of the Application used for the request
        self.assertEqual(audittrail.applicatie_weergave, self.applicatie.label)

    def test_audittrail_user_information(self):
        besluit_response = self._create_besluit()

        audittrail = AuditTrail.objects.filter(
            hoofd_object=besluit_response["url"]
        ).get()

        # Verify that the user id stored in the AuditTrail matches
        # the user id in the JWT token for the request
        self.assertIn(audittrail.gebruikers_id, self.user_id)

        # Verify that the user representation stored in the AuditTrail matches
        # the user representation in the JWT token for the request
        self.assertEqual(audittrail.gebruikers_weergave, self.user_representation)

    def test_audittrail_toelichting(self):
        toelichting = "blaaaa"
        besluit_data = self._create_besluit(HTTP_X_AUDIT_TOELICHTING=toelichting)

        audittrail = AuditTrail.objects.filter(hoofd_object=besluit_data["url"]).get()

        # Verify that the toelichting stored in the AuditTrail matches
        # the X-Audit-Toelichting header in the HTTP request
        self.assertEqual(audittrail.toelichting, toelichting)

    def test_read_audittrail(self):
        self._create_besluit()

        besluit = Besluit.objects.get()
        audittrails = AuditTrail.objects.get()
        audittrails_url = reverse(audittrails, kwargs={"besluit_uuid": besluit.uuid})

        response_audittrails = self.client.get(audittrails_url)

        self.assertEqual(response_audittrails.status_code, status.HTTP_200_OK)

    def test_audittrail_resource_weergave(self):
        besluit_response = self._create_besluit()

        besluit_uuid = get_uuid_from_path(besluit_response["url"])
        besluit_unique_representation = Besluit.objects.get(
            uuid=besluit_uuid
        ).unique_representation()

        audittrail = AuditTrail.objects.filter(
            hoofd_object=besluit_response["url"]
        ).get()

        # Verify that the resource weergave stored in the AuditTrail matches
        # the unique representation as defined in the besluit model
        self.assertIn(audittrail.resource_weergave, besluit_unique_representation)


class BesluitAuditTrailJWTExpiryTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @freeze_time("2019-01-01T12:00:00")
    def setUp(self):
        super().setUp()
        token = generate_jwt(
            self.client_id,
            self.secret,
            self.user_id,
            self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_besluit_audittrail_list_jwt_expired(self):
        besluit = BesluitFactory.create()
        url = reverse(besluit)

        AuditTrail.objects.create(hoofd_object=url, resource="Besluit", resultaat=200)

        audit_url = reverse(
            "audittrail-list",
            kwargs={"besluit_uuid": besluit.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_besluit_audittrail_detail_jwt_expired(self):
        besluit = BesluitFactory.create()
        url = reverse(besluit)

        audittrail = AuditTrail.objects.create(
            hoofd_object=url, resource="Besluit", resultaat=200
        )

        audit_url = reverse(
            "audittrail-detail",
            kwargs={"besluit_uuid": besluit.uuid, "uuid": audittrail.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")
