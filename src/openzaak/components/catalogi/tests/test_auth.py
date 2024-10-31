# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
import uuid

from django.test import override_settings

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase as _APITestCase
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ComponentTypes,
    RolOmschrijving,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import AuthCheckMixin, reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.selectielijst.tests import mock_selectielijst_oas_get
from openzaak.tests.utils import patch_resource_validator

from ..api.scopes import SCOPE_CATALOGI_FORCED_DELETE, SCOPE_CATALOGI_FORCED_WRITE
from ..constants import (
    InternExtern,
    RichtingChoices,
    SelectielijstKlasseProcestermijn as Procestermijn,
)
from ..models import (
    BesluitType,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from .base import APITestCase
from .factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)


class ReadTests(AuthCheckMixin, _APITestCase):
    def test_cannot_read_without_correct_scope(self):
        dummy_uuid = str(uuid.uuid4())
        urls = [
            # root
            reverse("catalogus-list"),
            reverse("catalogus-detail", kwargs={"uuid": dummy_uuid}),
            # nested one level
            reverse("zaaktype-list"),
            reverse("zaaktype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("informatieobjecttype-list"),
            reverse("informatieobjecttype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("besluittype-list"),
            reverse("besluittype-detail", kwargs={"uuid": dummy_uuid}),
            # nested two levels
            reverse("statustype-list"),
            reverse("statustype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("eigenschap-list"),
            reverse("eigenschap-detail", kwargs={"uuid": dummy_uuid}),
            reverse("roltype-list"),
            reverse("roltype-detail", kwargs={"uuid": dummy_uuid}),
            reverse("zaakobjecttype-list"),
            reverse("zaakobjecttype-detail", kwargs={"uuid": dummy_uuid}),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


class PublishedTypesForcedDeletionTests(APITestCase):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_DELETE]
    component = ComponentTypes.ztc

    def test_force_delete_besluittype_not_concept(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        response = self.client.delete(besluittype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BesluitType.objects.exists())

    def test_force_delete_besluittype_related_to_non_concept_resource(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)

        for resource in ["zaaktypen", "informatieobjecttypen"]:
            with self.subTest(resource=resource):
                related = zaaktype if resource == "zaaktypen" else informatieobjecttype
                besluittype = BesluitTypeFactory.create(**{resource: [related]})
                besluittype_url = reverse(besluittype)

                response = self.client.delete(besluittype_url)

                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(BesluitType.objects.exists())

    def test_force_delete_eigenschap_not_concept_zaaktype(self):
        eigenschap = EigenschapFactory.create(zaaktype__concept=False)
        eigenschap_url = reverse(eigenschap)

        response = self.client.delete(eigenschap_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Eigenschap.objects.exists())

    def test_force_delete_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_informatieobjecttype_related_to_non_concept_zaaktype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_informatieobjecttype_related_to_non_concept_besluittype(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()

        BesluitTypeFactory.create(
            informatieobjecttypen=[informatieobjecttype], concept=False
        )

        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.delete(informatieobjecttype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InformatieObjectType.objects.exists())

    def test_force_delete_ziot_not_concept_zaaktype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(zaaktype__concept=False)
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_force_delete_ziot_not_concept_informatieobjecttype(self):
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakTypeInformatieObjectType.objects.exists())

    def test_force_delete_resultaattype_not_concept_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_url = reverse(resultaattype)

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResultaatType.objects.exists())

    def test_force_delete_roltype_not_concept_zaaktype(self):
        roltype = RolTypeFactory.create(zaaktype__concept=False)
        roltype_url = reverse(roltype)

        response = self.client.delete(roltype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RolType.objects.exists())

    def test_force_delete_statustype_not_concept_zaaktype(self):
        statustype = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_url = reverse(statustype)

        response = self.client.delete(statustype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StatusType.objects.exists())

    def test_delete_zaaktype_fail_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())

    def test_force_delete_zaaktype_related_to_non_concept_besluittype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        BesluitTypeFactory.create(
            catalogus=catalogus, zaaktypen=[zaaktype], concept=False
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())

    def test_force_delete_zaaktype_related_to_non_concept_informatieobjecttype(self):
        catalogus = CatalogusFactory.create()

        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
        zaaktype_url = reverse(zaaktype)

        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=catalogus, concept=False, zaaktypen=[]
        )
        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )

        response = self.client.delete(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakType.objects.exists())


class PublishedTypesForcedWriteTests(APITestCase):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_WRITE]
    component = ComponentTypes.ztc

    def test_update_besluittype_not_concept(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "zaaktypen": [],
            "omschrijving": "test",
            "omschrijvingGeneriek": "",
            "besluitcategorie": "",
            "reactietermijn": "P14D",
            "publicatieIndicatie": True,
            "publicatietekst": "",
            "publicatietermijn": None,
            "toelichting": "aangepast",
            "informatieobjecttypen": [],
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(besluittype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        besluittype.refresh_from_db()
        self.assertEqual(besluittype.toelichting, "aangepast")

    def test_partial_update_besluittype_not_concept(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)

        response = self.client.patch(besluittype_url, {"toelichting": "ja"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        besluittype.refresh_from_db()
        self.assertEqual(besluittype.toelichting, "ja")

    def test_update_besluittype_related_to_non_concept_resources(self):
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=self.catalogus
        )
        besluittype = BesluitTypeFactory.create(
            zaaktypen=[zaaktype],
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        besluittype_url = reverse(besluittype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "zaaktypen": [f"http://testserver{reverse(zaaktype)}"],
            "omschrijving": "test",
            "omschrijvingGeneriek": "",
            "besluitcategorie": "",
            "reactietermijn": "P14D",
            "publicatieIndicatie": True,
            "publicatietekst": "",
            "publicatietermijn": None,
            "toelichting": "aangepast",
            "informatieobjecttypen": [
                f"http://testserver{reverse(informatieobjecttype)}"
            ],
            "beginGeldigheid": "2019-01-01",
        }

        response = self.client.put(besluittype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        besluittype.refresh_from_db()
        self.assertEqual(besluittype.toelichting, "aangepast")

    def test_partial_update_besluittype_related_to_non_concept_resources(self):
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=self.catalogus
        )
        besluittype = BesluitTypeFactory.create(
            zaaktypen=[zaaktype],
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        besluittype_url = reverse(besluittype)

        response = self.client.patch(besluittype_url, {"toelichting": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        besluittype.refresh_from_db()
        self.assertEqual(besluittype.toelichting, "aangepast")

    def test_create_eigenschap_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        eigenschap_list_url = reverse("eigenschap-list")
        data = {
            "naam": "Beoogd product",
            "definitie": "test",
            "toelichting": "",
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "specificatie": {
                "groep": "test",
                "formaat": "tekst",
                "lengte": "5",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        }

        response = self.client.post(eigenschap_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Eigenschap.objects.count(), 1)

    def test_update_eigenschap_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype)
        eigenschap_url = reverse(eigenschap)
        data = {
            "naam": "aangepast",
            "definitie": "test",
            "toelichting": "",
            "zaaktype": reverse(zaaktype),
            "specificatie": {
                "groep": "test",
                "formaat": "tekst",
                "lengte": "5",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        }

        response = self.client.put(eigenschap_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eigenschap.refresh_from_db()
        self.assertEqual(eigenschap.eigenschapnaam, "aangepast")

    def test_partial_update_eigenschap_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        eigenschap = EigenschapFactory.create(zaaktype=zaaktype)
        eigenschap_url = reverse(eigenschap)

        response = self.client.patch(eigenschap_url, {"naam": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eigenschap.refresh_from_db()
        self.assertEqual(eigenschap.eigenschapnaam, "aangepast")

    def test_update_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_partial_update_informatieobjecttype_not_concept(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "same"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "same")

    def test_update_informatieobjecttype_related_to_non_concept_resources(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus
        )
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        BesluitTypeFactory.create(
            concept=False,
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "main",
        }

        response = self.client.put(informatieobjecttype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_partial_update_informatieobjecttype_related_to_non_concept_resources(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=self.catalogus
        )
        zaaktype = ZaakTypeFactory.create(concept=False, catalogus=self.catalogus)
        ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        BesluitTypeFactory.create(
            concept=False,
            informatieobjecttypen=[informatieobjecttype],
            catalogus=self.catalogus,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(informatieobjecttype_url, {"omschrijving": "test"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        informatieobjecttype.refresh_from_db()
        self.assertEqual(informatieobjecttype.omschrijving, "test")

    def test_create_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=zaaktype.catalogus, zaaktypen=[]
        )
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "informatieobjecttype": f"http://testserver{reverse(informatieobjecttype)}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }
        url = reverse(ZaakTypeInformatieObjectType)

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakTypeInformatieObjectType.objects.count(), 1)

    def test_update_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False, zaaktypen=[]
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "informatieobjecttype": f"http://testserver{reverse(informatieobjecttype)}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_partial_update_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False, zaaktypen=[]
        )
        ziot = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 13})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_create_resultaattype_not_concept_zaaktype(self, mock_shape, mock_fetch, m):
        selectielijstklasse_url = "http://example.com/resultaten/1234"
        procestype_url = "http://referentielijsten.nl/procestypen/1234"
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        service = ServiceFactory.create(
            api_root="http://example.com/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            label="Selectielijst",
        )
        config = ReferentieLijstConfig.get_solo()
        config.service = service
        config.save()
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=procestype_url, concept=False
        )
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": selectielijstklasse_url,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }
        mock_selectielijst_oas_get(m)
        m.get(
            selectielijstklasse_url,
            json={
                "url": selectielijstklasse_url,
                "procesType": procestype_url,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})
        url = reverse(ResultaatType)

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ResultaatType.objects.count(), 1)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    @requests_mock.Mocker()
    def test_update_resultaattype_not_concept_zaaktype(self, mock_shape, mock_fetch, m):
        selectielijstklasse_url = "http://example.com/resultaten/1234"
        procestype_url = "http://referentielijsten.nl/procestypen/1234"
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        service = ServiceFactory.create(
            api_root="http://example.com/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            label="Selectielijst",
        )
        config = ReferentieLijstConfig.get_solo()
        config.service = service
        config.save()
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=procestype_url, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": selectielijstklasse_url,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }
        mock_selectielijst_oas_get(m)
        m.get(
            selectielijstklasse_url,
            json={
                "url": selectielijstklasse_url,
                "procesType": procestype_url,
                "procestermijn": Procestermijn.nihil,
            },
        )
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "test"})

        response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resultaattype.refresh_from_db()
        self.assertEqual(resultaattype.omschrijving, "aangepast")

    @requests_mock.Mocker()
    def test_partial_update_resultaattype_not_concept_zaaktype(self, m):
        procestype_url = "http://referentielijsten.nl/procestypen/1234"
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        m.get(resultaattypeomschrijving_url, json={"omschrijving": "init"})
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=procestype_url, concept=False
        )
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            archiefnominatie="blijvend_bewaren",
            resultaattypeomschrijving=resultaattypeomschrijving_url,
        )
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(resultaattype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resultaattype.refresh_from_db()
        self.assertEqual(resultaattype.omschrijving, "aangepast")

    def test_create_roltype_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        rol_type_list_url = reverse("roltype-list")
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "omschrijving": "Vergunningaanvrager",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.post(rol_type_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RolType.objects.count(), 1)

    def test_update_roltype_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)
        data = {
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": RolOmschrijving.initiator,
        }

        response = self.client.put(roltype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roltype.refresh_from_db()
        self.assertEqual(roltype.omschrijving, "aangepast")

    def test_partial_update_roltype_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        roltype = RolTypeFactory.create(zaaktype=zaaktype)
        roltype_url = reverse(roltype)

        response = self.client.patch(roltype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roltype.refresh_from_db()
        self.assertEqual(roltype.omschrijving, "aangepast")

    def test_create_statustype_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        statustype_list_url = reverse("statustype-list")
        data = {
            "omschrijving": "Besluit genomen",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "volgnummer": 2,
        }
        response = self.client.post(statustype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StatusType.objects.count(), 1)

    def test_update_statustype_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype_url = reverse(statustype)
        data = {
            "omschrijving": "aangepast",
            "omschrijvingGeneriek": "",
            "statustekst": "",
            "zaaktype": f"http://testserver{reverse(zaaktype)}",
            "volgnummer": 2,
        }

        response = self.client.put(statustype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statustype.refresh_from_db()
        self.assertEqual(statustype.statustype_omschrijving, "aangepast")

    def test_partial_update_statustype_not_concept_zaaktype(self):
        statustype = StatusTypeFactory.create(zaaktype__concept=False)
        statustype_url = reverse(statustype)

        response = self.client.patch(statustype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statustype.refresh_from_db()
        self.assertEqual(statustype.statustype_omschrijving, "aangepast")

    def test_update_zaaktype_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_partial_update_zaaktype_not_concept(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)

        response = self.client.patch(zaaktype_url, {"aanleiding": "same"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "same")

    def test_update_zaaktype_related_to_non_concept_besluittype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        zaaktype_url = reverse(zaaktype)
        BesluitTypeFactory.create(
            catalogus=self.catalogus, zaaktypen=[zaaktype], concept=False
        )
        data = {
            "identificatie": 0,
            "doel": "some test",
            "aanleiding": "aangepast",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "gerelateerdeZaaktypen": [],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "063308836",
        }

        response = self.client.put(zaaktype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")

    def test_partial_update_zaaktype_related_to_non_concept_besluittype(self):
        zaaktype = ZaakTypeFactory.create(catalogus=self.catalogus)
        zaaktype_url = reverse(zaaktype)
        BesluitTypeFactory.create(
            catalogus=self.catalogus, zaaktypen=[zaaktype], concept=False
        )

        response = self.client.patch(zaaktype_url, {"aanleiding": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaaktype.refresh_from_db()
        self.assertEqual(zaaktype.aanleiding, "aangepast")
