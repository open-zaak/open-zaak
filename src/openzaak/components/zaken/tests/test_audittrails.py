# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from copy import deepcopy

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.constants import VertrouwelijkheidsAanduiding, ZaakobjectTypes
from vng_api_common.tests import reverse
from vng_api_common.utils import get_uuid_from_path

from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..models import Resultaat, Zaak, ZaakInformatieObject, ZaakObject
from .factories import RolFactory, ZaakFactory, ZaakObjectFactory
from .utils import ZAAK_WRITE_KWARGS


class AuditTrailTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def _create_zaak(self, **headers):
        url = reverse(Zaak)
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        zaak_data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-12-24",
            "startdatum": "2018-12-24",
            "productenOfDiensten": ["https://example.com/product/123"],
        }
        response = self.client.post(url, zaak_data, **ZAAK_WRITE_KWARGS, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        return response.data

    def test_create_zaak_audittrail(self):
        zaak_response = self._create_zaak()

        audittrails = AuditTrail.objects.filter(hoofd_object=zaak_response["url"])
        self.assertEqual(audittrails.count(), 1)

        # Verify that the audittrail for the Zaak creation contains the correct
        # information
        zaak_create_audittrail = audittrails.get()
        self.assertEqual(zaak_create_audittrail.bron, "ZRC")
        self.assertEqual(zaak_create_audittrail.actie, "create")
        self.assertEqual(zaak_create_audittrail.resultaat, 201)
        self.assertEqual(zaak_create_audittrail.oud, None)
        self.assertEqual(zaak_create_audittrail.nieuw, zaak_response)

    def test_create_and_delete_resultaat_audittrails(self):
        zaak_response = self._create_zaak()
        zaak = Zaak.objects.get()

        resultaattype = ResultaatTypeFactory.create(zaaktype=zaak.zaaktype)
        resultaattype_url = reverse(resultaattype)
        url = reverse(Resultaat)
        resultaat_data = {
            "zaak": zaak_response["url"],
            "resultaattype": f"http://testserver{resultaattype_url}",
        }

        response = self.client.post(url, resultaat_data, **ZAAK_WRITE_KWARGS)

        resultaat_response = response.data

        audittrails = AuditTrail.objects.filter(
            hoofd_object=zaak_response["url"]
        ).order_by("pk")
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the Resultaat creation contains the
        # correct information
        resultaat_create_audittrail = audittrails[1]
        self.assertEqual(resultaat_create_audittrail.bron, "ZRC")
        self.assertEqual(resultaat_create_audittrail.actie, "create")
        self.assertEqual(resultaat_create_audittrail.resultaat, 201)
        self.assertEqual(resultaat_create_audittrail.oud, None)
        self.assertEqual(resultaat_create_audittrail.nieuw, resultaat_response)

        response = self.client.delete(resultaat_response["url"], **ZAAK_WRITE_KWARGS)
        self.assertEqual(audittrails.count(), 3)

        # Verify that the audittrail for the Resultaat deletion contains the
        # correct information
        resultaat_delete_audittrail = audittrails[2]
        self.assertEqual(resultaat_delete_audittrail.bron, "ZRC")
        self.assertEqual(resultaat_delete_audittrail.actie, "destroy")
        self.assertEqual(resultaat_delete_audittrail.resultaat, 204)
        self.assertEqual(resultaat_delete_audittrail.oud, resultaat_response)
        self.assertEqual(resultaat_delete_audittrail.nieuw, None)

    def test_update_zaak_audittrails(self):
        zaak_data = self._create_zaak()

        modified_data = deepcopy(zaak_data)
        url = modified_data.pop("url")
        modified_data.pop("verlenging")
        modified_data.pop("processobject")
        modified_data["toelichting"] = "aangepast"

        response = self.client.put(url, modified_data, **ZAAK_WRITE_KWARGS)
        zaak_response = response.data

        audittrails = AuditTrail.objects.filter(
            hoofd_object=zaak_response["url"]
        ).order_by("id")
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the Zaak update contains the correct
        # information
        zaak_update_audittrail = audittrails[1]
        self.assertEqual(zaak_update_audittrail.bron, "ZRC")
        self.assertEqual(zaak_update_audittrail.actie, "update")
        self.assertEqual(zaak_update_audittrail.resultaat, 200)
        self.assertEqual(zaak_update_audittrail.oud, zaak_data)
        self.assertEqual(zaak_update_audittrail.nieuw, zaak_response)

    def test_partial_update_zaak_audittrails(self):
        zaak_data = self._create_zaak()

        response = self.client.patch(
            zaak_data["url"], {"toelichting": "aangepast"}, **ZAAK_WRITE_KWARGS
        )
        zaak_response = response.data

        audittrails = AuditTrail.objects.filter(
            hoofd_object=zaak_response["url"]
        ).order_by("id")
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the Zaak partial_update contains the
        # correct information
        zaak_update_audittrail = audittrails[1]
        self.assertEqual(zaak_update_audittrail.bron, "ZRC")
        self.assertEqual(zaak_update_audittrail.actie, "partial_update")
        self.assertEqual(zaak_update_audittrail.resultaat, 200)
        self.assertEqual(zaak_update_audittrail.oud, zaak_data)
        self.assertEqual(zaak_update_audittrail.nieuw, zaak_response)

    def test_create_zaakinformatieobject_audittrail(self):
        zaak_data = self._create_zaak()
        zaak = Zaak.objects.get()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        url = reverse(ZaakInformatieObject)

        response = self.client.post(
            url,
            {
                "zaak": zaak_data["url"],
                "informatieobject": f"http://testserver{io_url}",
            },
        )
        zaakinformatieobject_response = response.data

        audittrails = AuditTrail.objects.filter(hoofd_object=zaak_data["url"]).order_by(
            "pk"
        )
        self.assertEqual(audittrails.count(), 2)

        # Verify that the audittrail for the ZaakInformatieObject creation
        # contains the correct information
        zio_create_audittrail = audittrails[1]
        self.assertEqual(zio_create_audittrail.bron, "ZRC")
        self.assertEqual(zio_create_audittrail.actie, "create")
        self.assertEqual(zio_create_audittrail.resultaat, 201)
        self.assertEqual(zio_create_audittrail.oud, None)
        self.assertEqual(zio_create_audittrail.nieuw, zaakinformatieobject_response)

    def test_delete_zaak_cascade_audittrails(self):
        zaak_data = self._create_zaak()

        # Delete the Zaak
        response = self.client.delete(zaak_data["url"], **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify that deleting the Zaak deletes all related AuditTrails
        audittrails = AuditTrail.objects.filter(hoofd_object=zaak_data["url"])
        self.assertFalse(audittrails.exists())

    def test_audittrail_applicatie_information(self):
        zaak_response = self._create_zaak()

        audittrail = AuditTrail.objects.filter(hoofd_object=zaak_response["url"]).get()

        # Verify that the application id stored in the AuditTrail matches
        # the id of the Application used for the request
        self.assertEqual(audittrail.applicatie_id, str(self.applicatie.uuid))

        # Verify that the application representation stored in the AuditTrail
        # matches the label of the Application used for the request
        self.assertEqual(audittrail.applicatie_weergave, self.applicatie.label)

    def test_audittrail_user_information(self):
        zaak_response = self._create_zaak()

        audittrail = AuditTrail.objects.filter(hoofd_object=zaak_response["url"]).get()

        # Verify that the user id stored in the AuditTrail matches
        # the user id in the JWT token for the request
        self.assertIn(audittrail.gebruikers_id, self.user_id)

        # Verify that the user representation stored in the AuditTrail matches
        # the user representation in the JWT token for the request
        self.assertEqual(audittrail.gebruikers_weergave, self.user_representation)

    def test_audittrail_toelichting(self):
        toelichting = "blaaaa"
        zaak_response = self._create_zaak(HTTP_X_AUDIT_TOELICHTING=toelichting)

        audittrail = AuditTrail.objects.filter(hoofd_object=zaak_response["url"]).get()

        # Verify that the toelichting stored in the AuditTrail matches
        # the X-Audit-Toelichting header in the HTTP request
        self.assertEqual(audittrail.toelichting, toelichting)

    def test_read_audittrail(self):
        self._create_zaak()

        zaak = Zaak.objects.get()
        audittrails = AuditTrail.objects.get()
        audittrails_url = reverse(audittrails, kwargs={"zaak_uuid": zaak.uuid})

        response_audittrails = self.client.get(audittrails_url)

        self.assertEqual(response_audittrails.status_code, status.HTTP_200_OK)

    def test_audittrail_resource_weergave(self):
        zaak_response = self._create_zaak()

        zaak_uuid = get_uuid_from_path(zaak_response["url"])
        zaak_unique_representation = Zaak.objects.get(
            uuid=zaak_uuid
        ).unique_representation()

        audittrail = AuditTrail.objects.filter(hoofd_object=zaak_response["url"]).get()

        # Verify that the resource weergave stored in the AuditTrail matches
        # the unique representation as defined in the Zaak model
        self.assertIn(audittrail.resource_weergave, zaak_unique_representation)

    def test_delete_rol(self):
        rol = RolFactory.create()

        rol_url = reverse(rol)
        zaak_url = reverse(rol.zaak)

        # Delete the Rol
        response = self.client.delete(rol_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        audittrail = AuditTrail.objects.get()
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}")
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject(self):
        url = reverse(ZaakObject)
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        data = {
            "zaak": zaak_url,
            "object": "http://example.org/api/zaakobjecten/8768c581-2817-4fe5-933d-37af92d819dd",
            "objectType": ZaakobjectTypes.besluit,
            "relatieomschrijving": "test",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        zaakobject_url = response.json()["url"]

        audittrail = AuditTrail.objects.get()
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}")
        self.assertEqual(audittrail.resource_url, zaakobject_url)

    def test_delete_zaakobject(self):
        zaakobject = ZaakObjectFactory.create()

        zaakobject_url = reverse(zaakobject)
        zaak_url = reverse(zaakobject.zaak)

        # Delete the Rol
        response = self.client.delete(zaakobject_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        audittrail = AuditTrail.objects.get()
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}")
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}")


class ZaakAuditTrailJWTExpiryTests(JWTAuthMixin, APITestCase):
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
    def test_zaak_audittrail_list_jwt_expired(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        AuditTrail.objects.create(hoofd_object=url, resource="Zaak", resultaat=200)

        audit_url = reverse(
            "audittrail-list",
            kwargs={"zaak_uuid": zaak.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")

    @override_settings(JWT_EXPIRY=60 * 60)
    @freeze_time("2019-01-01T13:00:00")
    def test_zaak_audittrail_detail_jwt_expired(self):
        zaak = ZaakFactory.create()
        url = reverse(zaak)

        audittrail = AuditTrail.objects.create(
            hoofd_object=url, resource="Zaak", resultaat=200
        )

        audit_url = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": audittrail.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["code"], "jwt-expired")
