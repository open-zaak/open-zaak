from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.models.tests.factories import RolTypeFactory
from openzaak.components.zaken.models import (
    Adres,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    Rol,
    SubVerblijfBuitenland,
    Vestiging,
)
from openzaak.components.zaken.models.constants import IndicatieMachtiging
from openzaak.components.zaken.models.tests.factories import RolFactory, ZaakFactory
from openzaak.utils.tests import JWTAuthMixin

from .utils import get_operation_url

BETROKKENE = (
    "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


class RolTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2018-01-01")
    def test_read_rol_np(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
        )
        naturlijkperson = NatuurlijkPersoon.objects.create(
            rol=rol, anp_identificatie="12345", inp_a_nummer="1234567890"
        )
        Adres.objects.create(
            natuurlijkpersoon=naturlijkperson,
            identificatie="123",
            postcode="1111",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test",
            huisnummer=1,
        )
        SubVerblijfBuitenland.objects.create(
            natuurlijkpersoon=naturlijkperson,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.natuurlijk_persoon,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "inpBsn": "",
                    "anpIdentificatie": "12345",
                    "inpA_nummer": "1234567890",
                    "geslachtsnaam": "",
                    "voorvoegselGeslachtsnaam": "",
                    "voorletters": "",
                    "voornamen": "",
                    "geslachtsaanduiding": "",
                    "geboortedatum": "",
                    "verblijfsadres": {
                        "aoaIdentificatie": "123",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test",
                        "aoaPostcode": "1111",
                        "aoaHuisnummer": 1,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "inpLocatiebeschrijving": "",
                    },
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
            },
        )

    @freeze_time("2018-01-01")
    def test_read_rol_nnp(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
        )
        nietnaturlijkperson = NietNatuurlijkPersoon.objects.create(
            rol=rol, ann_identificatie="123456"
        )
        SubVerblijfBuitenland.objects.create(
            nietnatuurlijkpersoon=nietnaturlijkperson,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.niet_natuurlijk_persoon,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "innNnpId": "",
                    "annIdentificatie": "123456",
                    "statutaireNaam": "",
                    "innRechtsvorm": "",
                    "bezoekadres": "",
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
            },
        )

    @freeze_time("2018-01-01")
    def test_read_rol_vestiging(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.vestiging,
            betrokkene=BETROKKENE,
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
            indicatie_machtiging=IndicatieMachtiging.gemachtigde,
        )
        vestiging = Vestiging.objects.create(rol=rol, vestigings_nummer="123456")
        Adres.objects.create(
            vestiging=vestiging,
            identificatie="123",
            postcode="1111",
            wpl_woonplaats_naam="test city",
            gor_openbare_ruimte_naam="test",
            huisnummer=1,
        )
        SubVerblijfBuitenland.objects.create(
            vestiging=vestiging,
            lnd_landcode="UK",
            lnd_landnaam="United Kingdom",
            sub_adres_buitenland_1="some uk adres",
        )
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype_url = reverse(rol.roltype)
        url = get_operation_url("rol_read", uuid=rol.uuid)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": BETROKKENE,
                "betrokkeneType": RolTypes.vestiging,
                "roltype": f"http://testserver{roltype_url}",
                "omschrijving": "Beslisser",
                "omschrijvingGeneriek": "Beslisser",
                "roltoelichting": "",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "gemachtigde",
                "betrokkeneIdentificatie": {
                    "vestigingsNummer": "123456",
                    "handelsnaam": [],
                    "verblijfsadres": {
                        "aoaIdentificatie": "123",
                        "wplWoonplaatsNaam": "test city",
                        "gorOpenbareRuimteNaam": "test",
                        "aoaPostcode": "1111",
                        "aoaHuisnummer": 1,
                        "aoaHuisletter": "",
                        "aoaHuisnummertoevoeging": "",
                        "inpLocatiebeschrijving": "",
                    },
                    "subVerblijfBuitenland": {
                        "lndLandcode": "UK",
                        "lndLandnaam": "United Kingdom",
                        "subAdresBuitenland_1": "some uk adres",
                        "subAdresBuitenland_2": "",
                        "subAdresBuitenland_3": "",
                    },
                },
            },
        )

    def test_create_rol_with_identificatie(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
            "betrokkeneIdentificatie": {
                "anpIdentificatie": "12345",
                "verblijfsadres": {
                    "aoaIdentificatie": "123",
                    "wplWoonplaatsNaam": "test city",
                    "gorOpenbareRuimteNaam": "test",
                    "aoaPostcode": "1111",
                    "aoaHuisnummer": 1,
                },
                "subVerblijfBuitenland": {
                    "lndLandcode": "UK",
                    "lndLandnaam": "United Kingdom",
                    "subAdresBuitenland_1": "some uk adres",
                },
            },
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(NatuurlijkPersoon.objects.count(), 1)
        self.assertEqual(NietNatuurlijkPersoon.objects.count(), 0)

        rol = Rol.objects.get()
        natuurlijk_persoon = NatuurlijkPersoon.objects.get()
        adres = Adres.objects.get()
        verblijf_buitenland = SubVerblijfBuitenland.objects.get()

        self.assertEqual(rol.natuurlijkpersoon, natuurlijk_persoon)
        self.assertEqual(natuurlijk_persoon.anp_identificatie, "12345")
        self.assertEqual(natuurlijk_persoon.verblijfsadres, adres)
        self.assertEqual(adres.identificatie, "123")
        self.assertEqual(
            natuurlijk_persoon.sub_verblijf_buitenland, verblijf_buitenland
        )
        self.assertEqual(verblijf_buitenland.lnd_landcode, "UK")

    def test_create_rol_without_identificatie(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(NatuurlijkPersoon.objects.count(), 0)

        rol = Rol.objects.get()

        self.assertEqual(rol.betrokkene, BETROKKENE)

    def test_create_rol_fail_validation(self):
        url = get_operation_url("rol_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(zaaktype=zaak.zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaak": f"http://testserver{zaak_url}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{roltype_url}",
            "roltoelichting": "awerw",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")

        self.assertEqual(validation_error["code"], "invalid-betrokkene")

    @freeze_time("2018-01-01")
    def test_filter_rol_np_bsn(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        NatuurlijkPersoon.objects.create(
            rol=rol, inp_bsn="183068142", inp_a_nummer="1234567890"
        )

        rol_2 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.natuurlijk_persoon,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        NatuurlijkPersoon.objects.create(
            rol=rol_2, inp_bsn="650237481", inp_a_nummer="2234567890"
        )

        rol_3 = RolFactory.create(
            zaak=zaak,
            betrokkene_type=RolTypes.vestiging,
            betrokkene="",
            omschrijving="Beslisser",
            omschrijving_generiek="Beslisser",
        )
        Vestiging.objects.create(rol=rol_3, vestigings_nummer="183068142")

        url = get_operation_url("rol_list", uuid=rol.uuid)

        response = self.client.get(
            url, {"betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "183068142"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["betrokkeneIdentificatie"]["inpBsn"], "183068142")
