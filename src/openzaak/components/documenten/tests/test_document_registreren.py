# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid
from base64 import b64encode
from datetime import date

from django.test import override_settings
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    ComponentTypes,
    RelatieAarden,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import (
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_AANMAKEN
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.tests.utils import get_operation_url
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_CREATE,
    SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN,
)
from openzaak.components.zaken.models import ZaakInformatieObject
from openzaak.components.zaken.tests.factories import (
    StatusFactory,
    ZaakFactory,
)
from openzaak.tests.utils import JWTAuthMixin


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class DocumentRegistrerenAuthTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("registreerdocument-list")
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim

    @classmethod
    def setUpClass(cls):
        APITestCase.setUpClass()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id, defaults={"secret": cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label="for test",
            heeft_alle_autorisaties=False,
        )

        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        cls.informatieobjecttype_url = cls.check_for_instance(cls.informatieobjecttype)

        cls.zaaktype = ZaakTypeFactory.create()
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=cls.zaaktype, informatieobjecttype=cls.informatieobjecttype
        )

    def _add_documenten_auth(self, informatieobjecttype=None, scopes=None):
        if scopes is None:
            scopes = []

        self.autorisatie = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.drc,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN] + scopes,
            zaaktype="",
            informatieobjecttype=self.informatieobjecttype_url
            if informatieobjecttype is None
            else informatieobjecttype,
            besluittype="",
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def _add_zaken_auth(self, zaaktype=None, scopes=None):
        if scopes is None:
            scopes = []

        self.autorisatie = Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_CREATE] + scopes,
            zaaktype=self.zaaktype_url if zaaktype is None else zaaktype,
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def _add_catalogi_auth(self, component: ComponentTypes, catalogus, scopes):
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=component,
            scopes=scopes,
            catalogus=catalogus,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(self.zaak)

        status_url = reverse(StatusFactory.create(zaak=self.zaak))

        self.content = {
            "enkelvoudiginformatieobject": {
                "identificatie": uuid.uuid4().hex,
                "bronorganisatie": "159351741",
                "creatiedatum": "2025-01-01",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": self.informatieobjecttype_url,
                "vertrouwelijkheidaanduiding": "geheim",
                "verschijningsvorm": "Vorm A",
                "trefwoorden": ["some", "other"],
            },
            "zaakinformatieobject": {
                "zaak": f"http://testserver{zaak_url}",
                "titel": "string",
                "beschrijving": "string",
                "vernietigingsdatum": "2019-08-24T14:15:22Z",
                "status": f"http://testserver{status_url}",
            },
        }

    def test_register_document(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_document_no_auth(self):
        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_no_zaken_auth(self):
        self._add_documenten_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_no_documenten_auth(self):
        self._add_documenten_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_invalid_vertrouwelijkheidaanduiding(self):
        self.max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar

        self._add_documenten_auth()
        self._add_zaken_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_no_zaakttype_in_auth(self):
        self._add_documenten_auth()
        self._add_zaken_auth(zaaktype="")

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_no_informatieobjecttype_in_auth(self):
        self._add_documenten_auth(informatieobjecttype="")
        self._add_zaken_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_with_catalogus_auths(self):
        self._add_catalogi_auth(
            ComponentTypes.drc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_document_with_drc_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.drc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_with_zrc_catalogus_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_register_document_with_zrc_catalogus_and_drc_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )
        self._add_documenten_auth()

        response = self.client.post(self.url, self.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_register_document_with_invalid_zaak_url(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        content = self.content.copy()
        content["zaakinformatieobject"]["zaak"] = "invalidurl"

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "object-does-not-exist")

    def test_register_document_without_zaak(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        content = self.content.copy()
        content["zaakinformatieobject"].pop("zaak")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "required")

    def test_register_document_without_informatieobjecttype(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        content = self.content.copy()
        content["enkelvoudiginformatieobject"].pop("informatieobjecttype")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(
            response, "enkelvoudiginformatieobject.informatieobjecttype"
        )
        self.assertEqual(error["code"], "required")

    def test_register_document_without_informatieobjecttype_catalogi_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.drc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )

        content = self.content.copy()
        content["enkelvoudiginformatieobject"].pop("informatieobjecttype")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(
            response, "enkelvoudiginformatieobject.informatieobjecttype"
        )
        self.assertEqual(error["code"], "required")

    def test_register_document_without_zaakinformatieobject(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        content = self.content.copy()
        content.pop("zaakinformatieobject")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "required")

    def test_register_document_without_zaakinformatieobject_catalogi_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.drc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )

        content = self.content.copy()
        content.pop("zaakinformatieobject")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "required")

    def test_register_document_without_enkelvoudiginformatieobject(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        content = self.content.copy()
        content.pop("enkelvoudiginformatieobject")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "enkelvoudiginformatieobject")
        self.assertEqual(error["code"], "required")

    def test_register_document_without_enkelvoudiginformatieobject_catalogi_auth(self):
        self._add_catalogi_auth(
            ComponentTypes.drc,
            self.informatieobjecttype.catalogus,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )
        self._add_catalogi_auth(
            ComponentTypes.zrc, self.zaaktype.catalogus, scopes=[SCOPE_ZAKEN_CREATE]
        )

        content = self.content.copy()
        content.pop("enkelvoudiginformatieobject")

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "enkelvoudiginformatieobject")
        self.assertEqual(error["code"], "required")

    def test_register_with_closed_zaak(self):
        self._add_zaken_auth()
        self._add_documenten_auth()

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(
            response.data["detail"],
            "Je mag geen gegevens aanpassen van een gesloten zaak.",
        )

    def test_register_with_closed_zaak_with_force_scope(self):
        self._add_zaken_auth(scopes=[SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN])
        self._add_documenten_auth()

        self.zaak.einddatum = timezone.now()
        self.zaak.save()

        self.assertTrue(self.zaak.is_closed)

        response = self.client.post(self.url, self.content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


@freeze_time("2025-01-01T12:00:00")
@override_settings(OPENZAAK_DOMAIN="testserver")
class DocumentRegistrerenValidationTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("registreerdocument-list")
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.zaak = ZaakFactory.create()
        self.zaak_url = reverse(self.zaak)

        self.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        self.informatieobjecttype_url = reverse(self.informatieobjecttype)

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=self.zaak.zaaktype, informatieobjecttype=self.informatieobjecttype
        )

        self.status = StatusFactory.create(zaak=self.zaak)
        self.status_url = reverse(self.status)

        self.enkelvoudiginformatieobject = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2025-01-01",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{self.informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
            "verschijningsvorm": "Vorm A",
            "trefwoorden": ["some", "other"],
        }

        self.zaakinformatieobject = {
            "zaak": f"http://testserver{self.zaak_url}",
            "titel": "string",
            "beschrijving": "string",
            "vernietigingsdatum": "2019-08-24T14:15:22Z",
            "status": f"http://testserver{self.status_url}",
        }

    def test_register_document(self):
        content = {
            "enkelvoudiginformatieobject": self.enkelvoudiginformatieobject,
            "zaakinformatieobject": self.zaakinformatieobject,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(
            eio.identificatie, content["enkelvoudiginformatieobject"]["identificatie"]
        )
        self.assertEqual(eio.bronorganisatie, "159351741")
        self.assertEqual(eio.creatiedatum, date(2025, 1, 1))
        self.assertEqual(eio.titel, "detailed summary")
        self.assertEqual(eio.auteur, "test_auteur")
        self.assertEqual(eio.formaat, "txt")
        self.assertEqual(eio.taal, "eng")
        self.assertEqual(eio.versie, 1)
        self.assertAlmostEqual(eio.begin_registratie, timezone.now())
        self.assertEqual(eio.bestandsnaam, "dummy.txt")
        self.assertEqual(eio.inhoud.read(), b"some file content")
        self.assertEqual(eio.link, "http://een.link")
        self.assertEqual(eio.beschrijving, "test_beschrijving")
        self.assertEqual(eio.informatieobjecttype, self.informatieobjecttype)
        self.assertEqual(eio.vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(eio.verschijningsvorm, "Vorm A")
        self.assertEqual(eio.trefwoorden, ["some", "other"])

        zio = ZaakInformatieObject.objects.get()
        self.assertEqual(zio.zaak, self.zaak)
        self.assertEqual(zio.aard_relatie, RelatieAarden.hoort_bij)
        self.assertEqual(zio.status, self.status)
        self.assertEqual(
            zio.vernietigingsdatum.isoformat(), "2019-08-24T14:15:22+00:00"
        )

        expected_eio_url = reverse(eio)
        expected_file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        expected_zio_url = reverse(zio)

        expected_response = {
            "enkelvoudiginformatieobject": content["enkelvoudiginformatieobject"]
            | {
                "url": f"http://testserver{expected_eio_url}",
                "inhoud": f"http://testserver{expected_file_url}?versie=1",
                "versie": 1,
                "bestandsdelen": [],
                "beginRegistratie": eio.begin_registratie.isoformat().replace(
                    "+00:00", "Z"
                ),
                "vertrouwelijkheidaanduiding": "openbaar",
                "bestandsomvang": eio.inhoud.size,
                "integriteit": {"algoritme": "", "waarde": "", "datum": None},
                "ontvangstdatum": None,
                "verzenddatum": None,
                "ondertekening": {"soort": "", "datum": None},
                "indicatieGebruiksrecht": None,
                "status": "",
                "locked": False,
                "lock": "",
                "verschijningsvorm": "Vorm A",
            },
            "zaakinformatieobject": content["zaakinformatieobject"]
            | {
                "url": f"http://testserver{expected_zio_url}",
                "uuid": str(zio.uuid),
                "informatieobject": f"http://testserver{expected_eio_url}",
                "titel": "string",
                "beschrijving": "string",
                "registratiedatum": "2025-01-01T12:00:00Z",
                "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
                "vernietigingsdatum": "2019-08-24T14:15:22Z",
            },
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_invalid_inhoud(self):
        content = {
            "enkelvoudiginformatieobject": self.enkelvoudiginformatieobject
            | {
                "inhoud": [1, 2, 3],
            },
            "zaakinformatieobject": self.zaakinformatieobject,
        }

        # Send to the API
        response = self.client.post(self.url, content)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)

        error = get_validation_errors(response, "enkelvoudiginformatieobject.inhoud")
        self.assertEqual(error["code"], "invalid")

    def test_no_zaaktypeinformatieobjecttype(self):
        zaak_url = reverse(ZaakFactory.create())

        content = {
            "enkelvoudiginformatieobject": self.enkelvoudiginformatieobject,
            "zaakinformatieobject": self.zaakinformatieobject
            | {
                "zaak": f"http://testserver{zaak_url}",
            },
        }

        # Send to the API
        response = self.client.post(self.url, content)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(
            error["code"], "missing-zaaktype-informatieobjecttype-relation"
        )

    def test_create_missing_enkelvoudiginformatieobject(self):
        content = {
            "zaakinformatieobject": self.zaakinformatieobject,
        }

        response = self.client.post(self.url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        self.assertEqual(len(response.data["invalid_params"]), 1)
        error = get_validation_errors(response, "enkelvoudiginformatieobject")
        self.assertEqual(error["code"], "required")
