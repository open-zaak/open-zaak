from unittest import skip

from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, RolOmschrijving
from vng_api_common.tests import reverse

from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_ALLES_LEZEN,
    SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
)
from openzaak.components.besluiten.models import Besluit
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ...documenten.tests.utils import serialise_eio
from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from .factories import (
    ResultaatFactory,
    RolFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)


@tag("closed-zaak")
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataNotAllowedCMISTests(JWTAuthMixin, APICMISTestCase):
    """
    Test that updating/adding related data of a Zaak is not allowed when the Zaak is
    closed.
    """

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype, closed=True)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.adapter.register_uri("GET", "https://example.com", status_code=200)
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def assertCreateBlocked(self, url: str, data: dict):
        with self.subTest(action="create"):
            response = self.client.post(url, data)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def assertUpdateBlocked(self, url: str):
        with self.subTest(action="update"):
            detail = self.client.get(url).data

            response = self.client.put(url, detail)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def assertPartialUpdateBlocked(self, url: str):
        with self.subTest(action="partial_update"):
            response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def assertDestroyBlocked(self, url: str):
        with self.subTest(action="destroy"):
            response = self.client.delete(url)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def test_zaakinformatieobjecten(self):
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.register_uri("GET", io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.register_uri("GET", io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobject__informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateBlocked(
            reverse(ZaakInformatieObject),
            {"zaak": reverse(self.zaak), "informatieobject": io1_url,},
        )
        self.assertUpdateBlocked(zio_url)
        self.assertPartialUpdateBlocked(zio_url)
        self.assertDestroyBlocked(zio_url)

    def test_zaakobjecten(self):
        self.assertCreateBlocked(
            reverse(ZaakObject),
            {
                "zaak": reverse(self.zaak),
                "object": "https://example.com",
                "objectType": "overige",
                "objectTypeOverige": "website",
            },
        )

    def test_zaakeigenschappen(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(zaak=self.zaak)
        eigenschap_url = reverse(zaak_eigenschap.eigenschap)

        self.assertCreateBlocked(
            reverse(ZaakEigenschap, kwargs={"zaak_uuid": self.zaak.uuid}),
            {
                "zaak": reverse(self.zaak),
                "eigenschap": f"http://testserver{eigenschap_url}",
                "waarde": "123",
            },
        )

    def test_klantcontacten(self):
        url = reverse(KlantContact)
        data = {
            "zaak": reverse(self.zaak),
            "datumtijd": "2020-01-30T15:08:00Z",
        }

        self.assertCreateBlocked(url, data)

    def test_rollen(self):
        roltype = RolTypeFactory.create(
            zaaktype=self.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        rol = RolFactory.create(
            zaak=self.zaak,
            roltype=roltype,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        rol_url = reverse(rol)

        create_url = reverse(Rol)
        data = {
            "zaak": reverse(self.zaak),
            "roltype": f"http://testserver{reverse(roltype)}",
            "betrokkeneType": "vestiging",
            "betrokkene": "https://example.com",
            "roltoelichting": "foo",
        }

        self.assertCreateBlocked(create_url, data)
        self.assertDestroyBlocked(rol_url)

    def test_resultaten(self):
        resultaat = ResultaatFactory.create(zaak=self.zaak)
        resultaat_url = reverse(resultaat)

        self.assertUpdateBlocked(resultaat_url)
        self.assertPartialUpdateBlocked(resultaat_url)
        self.assertDestroyBlocked(resultaat_url)

        resultaat.delete()

        data = {
            "zaak": reverse(self.zaak),
            "resultaattype": f"http://testserver{reverse(resultaat.resultaattype)}",
        }
        self.assertCreateBlocked(reverse(Resultaat), data)

    def test_zaakbesluiten(self):
        besluittype = BesluitTypeFactory.create(
            zaaktypen=[self.zaaktype], concept=False
        )
        besluittype_url = f"http://testserver{reverse(besluittype)}"
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=[
                SCOPE_BESLUITEN_AANMAKEN,
                SCOPE_BESLUITEN_ALLES_LEZEN,
                SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
            ],
            besluittype=besluittype_url,
        )

        self.assertCreateBlocked(
            reverse(Besluit),
            {
                "besluittype": besluittype_url,
                "zaak": f"http://testserver{reverse(self.zaak)}",
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
            },
        )

        besluit = BesluitFactory.create(zaak=self.zaak, besluittype=besluittype)
        self.assertDestroyBlocked(reverse(besluit))

    def test_statussen(self):
        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)

        self.assertCreateBlocked(
            reverse(Status),
            {
                "zaak": reverse(self.zaak),
                "statustype": f"http://testserver{reverse(statustype)}",
            },
        )


@tag("closed-zaak")
@override_settings(CMIS_ENABLED=True)
class ClosedZaakRelatedDataAllowedCMISTests(JWTAuthMixin, APICMISTestCase):
    """
    Test that updating/adding related data of a Zaak is not allowed when the Zaak is
    closed.
    """

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype, closed=True)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.adapter.register_uri("GET", "https://example.com", status_code=200)
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def assertCreateAllowed(self, url: str, data: dict):
        with self.subTest(action="create"):
            response = self.client.post(url, data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

    def assertUpdateAllowed(self, url: str):
        with self.subTest(action="update"):
            detail = self.client.get(url).data

            response = self.client.put(url, detail)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def assertPartialUpdateAllowed(self, url: str):
        with self.subTest(action="partial_update"):
            response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def assertDestroyAllowed(self, url: str):
        with self.subTest(action="destroy"):
            response = self.client.delete(url)

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )

    def test_zaakinformatieobjecten(self):
        io1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        io1_url = f"http://testserver{reverse(io1)}"
        self.adapter.register_uri("GET", io1_url, json=serialise_eio(io1, io1_url))

        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        io2_url = f"http://testserver{reverse(io2)}"
        self.adapter.register_uri("GET", io2_url, json=serialise_eio(io2, io2_url))
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject=io2_url,
            informatieobject__informatieobjecttype__zaaktypen__zaaktype=self.zaaktype,
            informatieobject__informatieobjecttype__catalogus=self.zaaktype.catalogus,
        )
        zio_url = reverse(zio)

        self.assertCreateAllowed(
            reverse(ZaakInformatieObject),
            {"zaak": reverse(self.zaak), "informatieobject": io1_url,},
        )
        self.assertUpdateAllowed(zio_url)
        self.assertPartialUpdateAllowed(zio_url)
        self.assertDestroyAllowed(zio_url)

    def test_zaakobjecten(self):
        self.assertCreateAllowed(
            reverse(ZaakObject),
            {
                "zaak": reverse(self.zaak),
                "object": "https://example.com",
                "objectType": "overige",
                "objectTypeOverige": "website",
            },
        )

    def test_zaakeigenschappen(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(zaak=self.zaak)
        eigenschap_url = reverse(zaak_eigenschap.eigenschap)

        self.assertCreateAllowed(
            reverse(ZaakEigenschap, kwargs={"zaak_uuid": self.zaak.uuid}),
            {
                "zaak": reverse(self.zaak),
                "eigenschap": f"http://testserver{eigenschap_url}",
                "waarde": "123",
            },
        )

    def test_klantcontacten(self):
        url = reverse(KlantContact)
        data = {
            "zaak": reverse(self.zaak),
            "datumtijd": "2020-01-30T15:08:00Z",
        }

        self.assertCreateAllowed(url, data)

    def test_rollen(self):
        roltype = RolTypeFactory.create(
            zaaktype=self.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        rol = RolFactory.create(zaak=self.zaak, roltype=roltype)
        rol_url = reverse(rol)

        create_url = reverse(Rol)
        data = {
            "zaak": reverse(self.zaak),
            "roltype": f"http://testserver{reverse(roltype)}",
            "betrokkeneType": "vestiging",
            "betrokkene": "https://example.com",
            "roltoelichting": "foo",
        }

        self.assertCreateAllowed(create_url, data)
        self.assertDestroyAllowed(rol_url)

    def test_resultaten(self):
        resultaat = ResultaatFactory.create(zaak=self.zaak)
        resultaat_url = reverse(resultaat)

        self.assertUpdateAllowed(resultaat_url)
        self.assertPartialUpdateAllowed(resultaat_url)
        self.assertDestroyAllowed(resultaat_url)

        resultaat.delete()

        data = {
            "zaak": reverse(self.zaak),
            "resultaattype": f"http://testserver{reverse(resultaat.resultaattype)}",
        }
        self.assertCreateAllowed(reverse(Resultaat), data)

    @skip("Complex case - API standard needs to decide first")
    def test_zaakbesluiten(self):
        besluittype = BesluitTypeFactory.create(
            zaaktypen=[self.zaaktype], concept=False
        )
        besluittype_url = f"http://testserver{reverse(besluittype)}"
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.brc,
            scopes=[
                SCOPE_BESLUITEN_AANMAKEN,
                SCOPE_BESLUITEN_ALLES_LEZEN,
                SCOPE_BESLUITEN_ALLES_VERWIJDEREN,
            ],
            besluittype=besluittype_url,
        )

        self.assertCreateAllowed(
            reverse(Besluit),
            {
                "besluittype": besluittype_url,
                "zaak": f"http://testserver{reverse(self.zaak)}",
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
            },
        )

        besluit = BesluitFactory.create(zaak=self.zaak, besluittype=besluittype)
        self.assertDestroyAllowed(reverse(besluit))
