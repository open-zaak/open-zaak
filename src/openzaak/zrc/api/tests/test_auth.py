"""
Guarantee that the proper authorization machinery is in place.
"""
import uuid
from unittest import skip

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, JWTAuthMixin, reverse

from openzaak.zrc.datamodel.models import ZaakInformatieObject
from openzaak.zrc.datamodel.tests.factories import (
    ResultaatFactory, RolFactory, StatusFactory, ZaakBesluitFactory,
    ZaakEigenschapFactory, ZaakFactory, ZaakInformatieObjectFactory,
    ZaakObjectFactory
)
from openzaak.zrc.tests.utils import ZAAK_READ_KWARGS

from ..scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_CREATE
)
from .mixins import ZaakInformatieObjectSyncMixin

INFORMATIEOBJECT = f'http://example.com/drc/api/v1/enkelvoudiginformatieobjecten/{uuid.uuid4().hex}'


@skip('Current implementation is without authentication')
@override_settings(ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient')
class ZakenScopeForbiddenTests(AuthCheckMixin, APITestCase):

    def test_cannot_create_zaak_without_correct_scope(self):
        url = reverse('zaak-list')
        self.assertForbidden(url, method='post')

    def test_cannot_read_without_correct_scope(self):
        zaak = ZaakFactory.create()
        status = StatusFactory.create()
        zaak_object = ZaakObjectFactory.create()
        resultaat = ResultaatFactory.create()
        urls = [
            reverse('zaak-list'),
            reverse(zaak),
            reverse('status-list'),
            reverse(status),
            reverse('status-list'),
            reverse(resultaat),
            reverse('zaakobject-list'),
            reverse(zaak_object),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method='get', request_kwargs=ZAAK_READ_KWARGS)


@skip('Current implementation is without authentication')
class ZaakReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar

    def test_zaak_list(self):
        """
        Assert you can only list ZAAKen of the zaaktypes and vertrouwelijkheidaanduiding
        of your authorization
        """
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse('zaak-list')

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['zaaktype'], 'https://zaaktype.nl/ok')
        self.assertEqual(results[0]['vertrouwelijkheidaanduiding'], VertrouwelijkheidsAanduiding.openbaar)

    def test_zaak_retreive(self):
        """
        Assert you can only read ZAAKen of the zaaktypes and vertrouwelijkheidaanduiding
        of your authorization
        """
        zaak1 = ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        zaak2 = ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse('zaak-list')

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']

        self.assertEqual(len(results), 4)


@skip('Current implementation is without authentication')
class StatusReadTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_resultaat_limited_to_authorized_zaken(self):
        url = reverse('status-list')
        # must show up
        status1 = StatusFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        StatusFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )
        # must not show up
        StatusFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]['url'],
            f"http://testserver{reverse(status1)}"
        )


@skip('Current implementation is without authentication')
class ResultaatTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_status_limited_to_authorized_zaken(self):
        url = reverse('resultaat-list')
        # must show up
        resultaat = ResultaatFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        ResultaatFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )
        # must not show up
        ResultaatFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]['url'],
            f"http://testserver{reverse(resultaat)}"
        )

    def test_write_operations_forbidden(self):
        # scope not provided for writes, so this should 403 (not 404!)
        resultaat = ResultaatFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        url = reverse(resultaat)

        for method in ['put', 'patch', 'delete']:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@skip('Current implementation is without authentication')
class ZaakObjectTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_zaakobject_limited_to_authorized_zaken(self):
        url = reverse('zaakobject-list')
        # must show up
        zaakobject = ZaakObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )
        # must not show up
        ZaakObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]['url'],
            f"http://testserver{reverse(zaakobject)}"
        )

    def test_create_zaakobject_limited_to_authorized_zaken(self):
        url = reverse('zaakobject-list')
        zaak1 = ZaakFactory.create(
            zaaktype='https://zaaktype.nl/not_ok'
        )
        zaak2 = ZaakFactory.create(
            zaaktype='https://zaaktype.nl/ok',
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        for zaak in [zaak1, zaak2]:
            with self.subTest(
                zaaktype=zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding
            ):
                response = self.client.post(url, {
                    "zaak": reverse(zaak),
                })

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@skip('Current implementation is without authentication')
class ZaakInformatieObjectTests(ZaakInformatieObjectSyncMixin, JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_zaakinformatieobject_limited_to_authorized_zaken(self):
        # must show up
        zio1 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            informatieobject=INFORMATIEOBJECT
        )
        # must not show up
        zio2 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            informatieobject=INFORMATIEOBJECT
        )
        # must not show up
        zio3 = ZaakInformatieObjectFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            informatieobject=INFORMATIEOBJECT
        )

        url = reverse(ZaakInformatieObject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        zaak_url = reverse(zio1.zaak)
        self.assertEqual(response.data[0]['zaak'], f'http://testserver{zaak_url}')


@skip('Current implementation is without authentication')
class ZaakEigenschapTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_zaakeigenschap_limited_to_authorized_zaken(self):
        # must show up
        eigenschap1 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap2 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap3 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        with self.subTest(
            zaaktype=eigenschap1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=eigenschap1.zaak.vertrouwelijkheidaanduiding
        ):
            url = reverse('zaakeigenschap-list', kwargs={'zaak_uuid': eigenschap1.zaak.uuid})
            eigenschap1_url = reverse(eigenschap1, kwargs={'zaak_uuid': eigenschap1.zaak.uuid})

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]['url'],
                f"http://testserver{eigenschap1_url}"
            )

        # not allowed to see these
        for eigenschap in (eigenschap2, eigenschap3):
            with self.subTest(
                zaaktype=eigenschap.zaak.zaaktype,
                vertrouwelijkheidaanduiding=eigenschap.zaak.vertrouwelijkheidaanduiding
            ):
                url = reverse('zaakeigenschap-list', kwargs={'zaak_uuid': eigenschap.zaak.uuid})

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_zaakeigenschap_limited_to_authorized_zaken(self):
        # must show up
        eigenschap1 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap2 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        eigenschap3 = ZaakEigenschapFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        with self.subTest(
            zaaktype=eigenschap1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=eigenschap1.zaak.vertrouwelijkheidaanduiding
        ):
            url = reverse(eigenschap1, kwargs={'zaak_uuid': eigenschap1.zaak.uuid})

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for eigenschap in (eigenschap2, eigenschap3):
            with self.subTest(
                zaaktype=eigenschap.zaak.zaaktype,
                vertrouwelijkheidaanduiding=eigenschap.zaak.vertrouwelijkheidaanduiding
            ):
                url = reverse(eigenschap, kwargs={'zaak_uuid': eigenschap.zaak.uuid})

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@skip('Current implementation is without authentication')
class RolReadTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_rol_limited_to_authorized_zaken(self):
        url = reverse('rol-list')
        # must show up
        rol = RolFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        RolFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )
        # must not show up
        RolFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]['url'],
            f"http://testserver{reverse(rol)}"
        )


@skip('Current implementation is without authentication')
class ZaakBesluitTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    zaaktype = 'https://zaaktype.nl/ok'
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.beperkt_openbaar

    def test_list_zaakbesluit_limited_to_authorized_zaken(self):
        # must show up
        zaak_besluit1 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        zaak_besluit2 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        zaak_besluit3 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        with self.subTest(
            zaaktype=zaak_besluit1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaak_besluit1.zaak.vertrouwelijkheidaanduiding
        ):
            url = reverse('zaakbesluit-list', kwargs={'zaak_uuid': zaak_besluit1.zaak.uuid})
            zio1_url = reverse(zaak_besluit1, kwargs={'zaak_uuid': zaak_besluit1.zaak.uuid})

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()
            self.assertEqual(len(response_data), 1)
            self.assertEqual(
                response_data[0]['url'],
                f"http://testserver{zio1_url}"
            )

        # not allowed to see these
        for zaak_besluit in (zaak_besluit2, zaak_besluit3):
            with self.subTest(
                zaaktype=zaak_besluit.zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak_besluit.zaak.vertrouwelijkheidaanduiding
            ):
                url = reverse('zaakbesluit-list', kwargs={'zaak_uuid': zaak_besluit.zaak.uuid})

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_zaakinformatieobject_limited_to_authorized_zaken(self):
        # must show up
        zaak_besluit1 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        zaak_besluit2 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/not_ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # must not show up
        zaak_besluit3 = ZaakBesluitFactory.create(
            zaak__zaaktype='https://zaaktype.nl/ok',
            zaak__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk
        )

        with self.subTest(
            zaaktype=zaak_besluit1.zaak.zaaktype,
            vertrouwelijkheidaanduiding=zaak_besluit1.zaak.vertrouwelijkheidaanduiding
        ):
            url = reverse(zaak_besluit1, kwargs={'zaak_uuid': zaak_besluit1.zaak.uuid})

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for zaak_besluit in (zaak_besluit2, zaak_besluit3):
            with self.subTest(
                zaaktype=zaak_besluit.zaak.zaaktype,
                vertrouwelijkheidaanduiding=zaak_besluit.zaak.vertrouwelijkheidaanduiding
            ):
                url = reverse(zaak_besluit, kwargs={'zaak_uuid': zaak_besluit.zaak.uuid})

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
