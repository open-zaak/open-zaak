# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

import datetime
from unittest import skip

from django.test import tag
from django.utils import timezone

import requests_mock
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import (
    Archiefnominatie,
    ComponentTypes,
    RolOmschrijving,
)
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
    InformatieObjectTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
    SCOPEN_ZAKEN_HEROPENEN,
)
from ..constants import BetalingsIndicatie
from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from .assertions import CRUDAssertions
from .factories import (
    ResultaatFactory,
    RolFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


class ZaakClosedTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create()
        super().setUpTestData()

    def test_update_zaak_open(self):
        zaak = ZaakFactory.create(
            betalingsindicatie=BetalingsIndicatie.geheel, zaaktype=self.zaaktype
        )
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.json()["betalingsindicatie"], BetalingsIndicatie.nvt)
        zaak.refresh_from_db()
        self.assertEqual(zaak.betalingsindicatie, BetalingsIndicatie.nvt)

    def test_update_zaak_closed_not_allowed(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype, closed=True)
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_zaak_closed_allowed(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype, closed=True)
        url = reverse(zaak)

        self.autorisatie.scopes = [SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN]
        self.autorisatie.save()

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_reopenzaak_allowed(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now().date(),
            archiefactiedatum="2020-01-01",
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            zaaktype=self.zaaktype,
        )
        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)
        StatusTypeFactory.create(zaaktype=self.zaaktype)
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url("status_create")

        self.autorisatie.scopes = [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        data = {
            "zaak": reverse(zaak),
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)
        self.assertIsNone(zaak.archiefactiedatum)
        self.assertIsNone(zaak.archiefnominatie)

    def test_reopenzaak_not_allowed(self):
        zaak = ZaakFactory.create(
            einddatum=timezone.now().date(), zaaktype=self.zaaktype
        )
        statustype = StatusTypeFactory.create(zaaktype=self.zaaktype)
        StatusTypeFactory.create(zaaktype=self.zaaktype)
        statustype_url = reverse(statustype)
        StatusTypeFactory.create()
        status_create_url = get_operation_url("status_create")
        self.autorisatie.scopes = [SCOPE_STATUSSEN_TOEVOEGEN]
        self.autorisatie.save()

        data = {
            "zaak": reverse(zaak),
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": datetime.datetime.now().isoformat(),
        }
        response = self.client.post(status_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        data = response.json()
        self.assertEqual(
            data["detail"],
            "Het heropenen van een gesloten zaak is niet toegestaan zonder de scope zaken.heropenen",
        )


@tag("closed-zaak")
@temp_private_root()
class ClosedZaakRelatedDataNotAllowedTests(JWTAuthMixin, CRUDAssertions, APITestCase):
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

        m = requests_mock.Mocker()
        m.start()
        m.get("https://example.com", status_code=200)
        self.addCleanup(m.stop)

    def test_zaakinformatieobjecten(self):
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.zaaktype.catalogus, zaaktypen__zaaktype=self.zaaktype
        )
        io = EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iotype)
        io_url = reverse(io)
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak,
            informatieobject__latest_version__informatieobjecttype=iotype,
        )
        zio_url = reverse(zio)

        self.assertCreateBlocked(
            reverse(ZaakInformatieObject),
            {
                "zaak": reverse(self.zaak),
                "informatieobject": f"http://testserver{io_url}",
            },
        )
        self.assertUpdateBlocked(zio_url)
        self.assertPartialUpdateBlocked(zio_url)
        self.assertDestroyBlocked(zio_url)

    def test_zaakobjecten(self):
        zaakobject = ZaakObjectFactory.create(
            zaak=self.zaak,
            object="https://example.com",
            zaakobjecttype="https://externe.catalogus.nl/api/v1/",
            relatieomschrijving="old",
        )
        zaakobject_url = reverse(zaakobject)

        self.assertCreateBlocked(
            reverse(ZaakObject),
            {
                "zaak": reverse(self.zaak),
                "object": "https://example.com",
                "objectType": "overige",
                "objectTypeOverige": "website",
            },
        )
        self.assertPartialUpdateBlocked(zaakobject_url)
        self.assertUpdateBlocked(
            zaakobject_url,
            data={"zaak": reverse(self.zaak), "objectTypeOverige": "website"},
        )
        self.assertDestroyBlocked(zaakobject_url)

    def test_zaakeigenschappen(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(zaak=self.zaak)
        eigenschap_url = reverse(zaak_eigenschap.eigenschap)

        data = {
            "zaak": reverse(self.zaak),
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "123",
        }
        self.assertCreateBlocked(
            reverse(ZaakEigenschap, kwargs={"zaak_uuid": self.zaak.uuid}), data
        )
        zaakeigenschap_url = reverse(
            zaak_eigenschap, kwargs={"zaak_uuid": self.zaak.uuid}
        )

        self.assertUpdateBlocked(zaakeigenschap_url, data=data)
        self.assertPartialUpdateBlocked(zaakeigenschap_url)
        self.assertDestroyBlocked(zaakeigenschap_url)

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
            "contactpersoon_rol_naam": "new",
        }

        self.assertCreateBlocked(create_url, data)
        self.assertUpdateBlocked(rol_url, data=data)
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
        besluit_url = reverse(besluit)
        self.assertPartialUpdateBlocked(besluit_url)
        self.assertUpdateBlocked(besluit_url)
        self.assertDestroyBlocked(besluit_url)

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
@temp_private_root()
class ClosedZaakRelatedDataAllowedTests(JWTAuthMixin, CRUDAssertions, APITestCase):
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

        m = requests_mock.Mocker()
        m.start()
        m.get("https://example.com", status_code=200)
        self.addCleanup(m.stop)

    def test_zaakinformatieobjecten(self):
        iotype = InformatieObjectTypeFactory.create(
            catalogus=self.zaaktype.catalogus, zaaktypen__zaaktype=self.zaaktype
        )
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iotype,
        )
        io_url = reverse(io)
        io2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iotype,
        )
        zio = ZaakInformatieObjectFactory(
            zaak=self.zaak, informatieobject=io2.canonical
        )
        zio_url = reverse(zio)

        self.assertCreateAllowed(
            reverse(ZaakInformatieObject),
            {
                "zaak": reverse(self.zaak),
                "informatieobject": f"http://testserver{io_url}",
            },
        )
        self.assertUpdateAllowed(zio_url)
        self.assertPartialUpdateAllowed(zio_url)
        self.assertDestroyAllowed(zio_url)

    def test_zaakobjecten(self):
        zaakobject = ZaakObjectFactory.create(
            zaak=self.zaak,
            object="https://example.com",
            zaakobjecttype="https://externe.catalogus.nl/api/v1/",
            relatieomschrijving="old",
        )
        zaakobject_url = reverse(zaakobject)
        self.assertCreateAllowed(
            reverse(ZaakObject),
            {
                "zaak": reverse(self.zaak),
                "object": "https://example.com",
                "objectType": "overige",
                "objectTypeOverige": "website",
            },
        )
        self.assertPartialUpdateAllowed(zaakobject_url)
        self.assertUpdateAllowed(
            zaakobject_url,
            data={"zaak": reverse(self.zaak), "objectTypeOverige": "website"},
        )
        self.assertDestroyAllowed(zaakobject_url)

    def test_zaakeigenschappen(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(zaak=self.zaak)
        eigenschap_url = reverse(zaak_eigenschap.eigenschap)
        data = {
            "zaak": reverse(self.zaak),
            "eigenschap": f"http://testserver{eigenschap_url}",
            "waarde": "123",
        }
        self.assertCreateAllowed(
            reverse(ZaakEigenschap, kwargs={"zaak_uuid": self.zaak.uuid}), data
        )

        zaakeigenschap_url = reverse(
            zaak_eigenschap, kwargs={"zaak_uuid": self.zaak.uuid}
        )

        self.assertUpdateAllowed(zaakeigenschap_url, data=data)
        self.assertPartialUpdateAllowed(zaakeigenschap_url)
        self.assertDestroyAllowed(zaakeigenschap_url)

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
            "contactpersoon_rol_naam": "new",
        }
        self.assertCreateAllowed(create_url, data)
        self.assertUpdateAllowed(rol_url, data=data)
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
        besluit_url = reverse(besluit)
        self.assertPartialUpdateAllowed(besluit_url)
        self.assertUpdateAllowed(besluit_url)
        self.assertDestroyAllowed(besluit_url)
