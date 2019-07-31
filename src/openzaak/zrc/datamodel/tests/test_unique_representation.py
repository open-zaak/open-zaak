from django.test import override_settings

from rest_framework.test import APITestCase
from zds_client.tests.mocks import mock_client

from openzaak.zrc.api.tests.mixins import ZaakInformatieObjectSyncMixin

from .factories import (
    KlantContactFactory, ResultaatFactory, RolFactory, StatusFactory,
    ZaakEigenschapFactory, ZaakFactory, ZaakInformatieObjectFactory,
    ZaakObjectFactory
)


@override_settings(
    ZDS_CLIENT_CLASS='vng_api_common.mocks.MockClient',
)
class UniqueRepresentationTestCase(ZaakInformatieObjectSyncMixin, APITestCase):

    def test_zaak(self):
        zaak = ZaakFactory(
            bronorganisatie=730924658,
            identificatie='5d940d52-ff5e-4b18-a769-977af9130c04'
        )

        self.assertEqual(
            zaak.unique_representation(),
            '730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04'
        )

    def test_status(self):
        status = StatusFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            datum_status_gezet='2019-05-01T00:00:00+0000',
        )

        self.assertEqual(
            status.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 2019-05-01T00:00:00+0000'
        )

    def test_resultaat(self):
        resultaat = ResultaatFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
        )
        responses = {
            resultaat.resultaattype: {
                'url': resultaat.resultaattype,
                'omschrijving': "verleend",
            }
        }

        with mock_client(responses):
            unique_representation = resultaat.unique_representation()

        self.assertEqual(
            unique_representation,
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - verleend'
        )

    def test_rol_betrikkene_with_uuid(self):
        rol = RolFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            betrokkene='http://example.come/api/betrokkene/255aaec2-d269-480c-adab-d5d7bc7f9987'
        )

        self.assertEqual(
            rol.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 255aaec2-d269-480c-adab-d5d7bc7f9987'
        )

    def test_rol_betrokkene_without_uuid(self):
        rol = RolFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            betrokkene='http://example.come/api/betrokkene/some-betrokkene'
        )

        self.assertEqual(
            rol.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some-betrokkene'
        )

    def test_rol_without_betrokkene(self):
        rol = RolFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            betrokkene='',
            roltoelichting='some role'
        )

        self.assertEqual(
            rol.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some role'
        )

    def test_zaakobject_object_with_uuid(self):
        zaakobject = ZaakObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            object='http://example.come/api/objects/255aaec2-d269-480c-adab-d5d7bc7f9987'
        )

        self.assertEqual(
            zaakobject.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 255aaec2-d269-480c-adab-d5d7bc7f9987'
        )

    def test_zaakobject_object_without_uuid(self):
        zaakobject = ZaakObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            object='http://example.come/api/objects/some-object'
        )

        self.assertEqual(
            zaakobject.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some-object'
        )

    def test_zaakobject_without_object(self):
        zaakobject = ZaakObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            object='',
            relatieomschrijving='some description'
        )

        self.assertEqual(
            zaakobject.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some description'
        )

    def test_zaakeigenschap(self):
        zaakeigenschap = ZaakEigenschapFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04',
            _naam='brondatum'
        )

        self.assertEqual(
            zaakeigenschap.unique_representation(),
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - brondatum'
        )

    def test_zaakinformatieobject(self):
        zio = ZaakInformatieObjectFactory(
            zaak__bronorganisatie=730924658,
            zaak__identificatie='5d940d52-ff5e-4b18-a769-977af9130c04'
        )
        responses = {
            zio.informatieobject: {
                'url': zio.informatieobject,
                'identificatie': "12345",
            }
        }
        with mock_client(responses):
            unique_representation = zio.unique_representation()

        self.assertEqual(
            unique_representation,
            '(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345'
        )

    def test_klancontact(self):
        klancontact = KlantContactFactory(identificatie=777)
        self.assertEqual(
            klancontact.unique_representation(),
            '777'
        )
