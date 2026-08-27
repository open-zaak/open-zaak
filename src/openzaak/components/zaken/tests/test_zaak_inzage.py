# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
import uuid
from urllib.parse import urljoin

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ComponentTypes,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.besluiten.api.scopes import SCOPE_BESLUITEN_ALLES_LEZEN
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.api.scopes import SCOPE_CATALOGI_READ
from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
from openzaak.tests.utils.auth import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import OrganisatorischeEenheid
from .factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    SubStatusFactory,
    ZaakContactMomentFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakNotitieFactory,
    ZaakObjectFactory,
    ZaakVerzoekFactory,
)
from .utils import ZAAK_READ_KWARGS


class ZaakInzageAuthTests(JWTAuthMixin, APITestCase):
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
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = cls.check_for_instance(cls.zaaktype)

    def setUp(self):
        super().setUp()
        self.zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.url = reverse("zaken:zaakinzage", kwargs={"uuid": self.zaak.uuid})

    def _add_auth(self, scopes, zaaktype=None):
        return Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=scopes,
            zaaktype=self.zaaktype_url if zaaktype is None else zaaktype,
            informatieobjecttype="",
            besluittype="",
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

    def test_retrieve_with_required_scopes(self):
        self._add_auth(
            [
                SCOPE_ZAKEN_ALLES_LEZEN,
                SCOPE_CATALOGI_READ,
                SCOPE_BESLUITEN_ALLES_LEZEN,
            ]
        )

        response = self.client.get(self.url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_retrieve_without_authorization(self):
        response = self.client.get(self.url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_retrieve_with_only_one_required_scope(self):
        required_scopes = [
            SCOPE_ZAKEN_ALLES_LEZEN,
            SCOPE_CATALOGI_READ,
            SCOPE_BESLUITEN_ALLES_LEZEN,
        ]

        for scope in required_scopes:
            with self.subTest(scope=scope):
                authorization = self._add_auth([scope])

                response = self.client.get(self.url, **ZAAK_READ_KWARGS)

                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN, response.data
                )
                authorization.delete()

    def test_retrieve_with_only_two_required_scopes(self):
        required_scopes = [
            SCOPE_ZAKEN_ALLES_LEZEN,
            SCOPE_CATALOGI_READ,
            SCOPE_BESLUITEN_ALLES_LEZEN,
        ]

        for missing_scope in required_scopes:
            with self.subTest(missing_scope=missing_scope):
                authorization = self._add_auth(
                    [scope for scope in required_scopes if scope != missing_scope]
                )

                response = self.client.get(self.url, **ZAAK_READ_KWARGS)

                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN, response.data
                )
                authorization.delete()

    def test_retrieve_with_authorization_for_different_zaaktype(self):
        other_zaaktype = ZaakTypeFactory.create(concept=False)
        self._add_auth(
            [
                SCOPE_ZAKEN_ALLES_LEZEN,
                SCOPE_CATALOGI_READ,
                SCOPE_BESLUITEN_ALLES_LEZEN,
            ],
            zaaktype=self.check_for_instance(other_zaaktype),
        )

        response = self.client.get(self.url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_retrieve_with_catalogus_authorization(self):
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[
                SCOPE_ZAKEN_ALLES_LEZEN,
                SCOPE_CATALOGI_READ,
                SCOPE_BESLUITEN_ALLES_LEZEN,
            ],
            catalogus=self.zaaktype.catalogus,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        response = self.client.get(self.url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)


class ZaakInzageTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def _format_url(self, path: str) -> str:
        return str(urljoin("http://testserver", path))

    def _format_dt(self, value) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _format_date(self, value) -> str:
        return value.strftime("%Y-%m-%d")

    def setUp(self):
        super().setUp()
        self.zaaktype = ZaakTypeFactory.create(concept=False, verlenging_mogelijk=False)

        self.zaak = ZaakFactory(zaaktype=self.zaaktype)

        self.url = reverse("zaken:zaakinzage", kwargs={"uuid": self.zaak.uuid})

    def test_get_complete_zaak_inzage(self):
        zaak = self.zaak
        zaaktype = self.zaaktype

        # Prepare zaaktype related data
        eigenschaptype = EigenschapFactory(zaaktype=zaaktype)
        resultaattype = ResultaatTypeFactory(
            zaaktype=zaaktype,
            brondatum_archiefprocedure_afleidingswijze=Afleidingswijze.afgehandeld.value,
        )
        roltype = RolTypeFactory.create(
            zaaktype=zaaktype,
        )
        statustype = StatusTypeFactory(zaaktype=zaaktype)
        zaakobjecttype = ZaakObjectTypeFactory(zaaktype=zaaktype)
        zaaktypeinformatieobjecttype = ZaakTypeInformatieObjectTypeFactory(
            zaaktype=zaaktype
        )

        # Prepare zaak related data
        zaakeigenschaap = ZaakEigenschapFactory(zaak=zaak, eigenschap=eigenschaptype)
        resultaat = ResultaatFactory(zaak=zaak, resultaattype=resultaattype)

        rol = RolFactory.create(
            zaak=zaak,
            roltype=roltype,
            betrokkene_type=RolTypes.organisatorische_eenheid,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        OrganisatorischeEenheid.objects.create(identificatie="OE1", rol=rol)

        zaakstatus = StatusFactory(
            zaak=zaak,
            statustype=statustype,
        )
        substatus = SubStatusFactory(
            zaak=zaak,
            status=zaakstatus,
        )
        zaakcontactmoment = ZaakContactMomentFactory(zaak=zaak)
        zaakinformatieobject = ZaakInformatieObjectFactory(
            zaak=zaak,
        )
        zaakobject = ZaakObjectFactory(zaak=zaak, object_type=ZaakobjectTypes.besluit)
        zaakverzoek = ZaakVerzoekFactory(zaak=zaak)
        zaaknotitie = ZaakNotitieFactory(gerelateerd_aan=zaak)

        besluit = BesluitFactory.create(for_zaak=True, zaak=zaak)

        response = self.client.get(self.url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        expected_zaak_url = self._format_url(reverse(zaak))
        expected_zaaktype_catalogus_url = self._format_url(reverse(zaaktype.catalogus))

        # Assert _expand is not included in the data
        self.assertNotIn("_expand", data)

        self.assertEqual(data["url"], self._format_url(reverse(zaak)))
        self.assertEqual(data["resultaat"]["url"], self._format_url(reverse(resultaat)))
        self.assertEqual(
            data["rollen"][0]["roltype"], self._format_url(reverse(roltype))
        )
        self.assertEqual(
            data["statussen"][0]["statustype"],
            self._format_url(reverse(statustype)),
        )
        self.assertEqual(data["status"]["uuid"], str(zaakstatus.uuid))
        self.assertEqual(len(data["status"]["substatussen"]), 1)
        self.assertEqual(len(data["statussen"][0]["substatussen"]), 1)

        # Assert zaak relations has 1 data
        for relation in (
            "eigenschappen",
            "besluiten",
            "rollen",
            "statussen",
            "zaakcontactmomenten",
            "zaakinformatieobjecten",
            "zaakobjecten",
            "zaakverzoeken",
            "zaaknotities",
        ):
            self.assertEqual(len(data[relation]), 1, relation)

        # Assert zaaktype relations has 1 data
        nested_zaaktype = data["zaaktype"]
        self.assertNotIn("_expand", nested_zaaktype)
        for relation in (
            "eigenschappen",
            "resultaattypen",
            "roltypen",
            "statustypen",
            "zaakobjecttypen",
            "informatieobjecttypen",
        ):
            self.assertEqual(len(nested_zaaktype[relation]), 1, relation)

        expected_response = {
            "url": expected_zaak_url,
            "uuid": str(zaak.uuid),
            "identificatie": zaak.identificatie,
            "bronorganisatie": zaak.bronorganisatie,
            "omschrijving": zaak.omschrijving,
            "toelichting": "",
            "zaaktype": {
                "url": self._format_url(reverse(zaaktype)),
                "identificatie": zaaktype.identificatie,
                "omschrijving": zaaktype.zaaktype_omschrijving,
                "omschrijvingGeneriek": "",
                "vertrouwelijkheidaanduiding": "",
                "doel": zaaktype.doel,
                "aanleiding": zaaktype.aanleiding,
                "toelichting": "",
                "indicatieInternOfExtern": zaaktype.indicatie_intern_of_extern,
                "handelingInitiator": zaaktype.handeling_initiator,
                "onderwerp": zaaktype.onderwerp,
                "handelingBehandelaar": zaaktype.handeling_behandelaar,
                "doorlooptijd": "P30D",
                "servicenorm": None,
                "opschortingEnAanhoudingMogelijk": zaaktype.opschorting_en_aanhouding_mogelijk,
                "verlengingMogelijk": zaaktype.verlenging_mogelijk,
                "verlengingstermijn": None,
                "trefwoorden": [],
                "publicatieIndicatie": zaaktype.publicatie_indicatie,
                "publicatietekst": zaaktype.publicatietekst,
                "verantwoordingsrelatie": zaaktype.verantwoordingsrelatie,
                "productenOfDiensten": zaaktype.producten_of_diensten,
                "selectielijstProcestype": zaaktype.selectielijst_procestype,
                "referentieproces": {
                    "naam": zaaktype.referentieproces_naam,
                    "link": "",
                },
                "concept": zaaktype.concept,
                "verantwoordelijke": zaaktype.verantwoordelijke,
                "broncatalogus": {"url": "", "domein": "", "rsin": ""},
                "bronzaaktype": {
                    "url": "",
                    "identificatie": "",
                    "omschrijving": "",
                },
                "beginGeldigheid": self._format_date(zaaktype.datum_begin_geldigheid),
                "eindeGeldigheid": None,
                "versiedatum": self._format_date(zaaktype.versiedatum),
                "beginObject": self._format_date(zaaktype.datum_begin_geldigheid),
                "eindeObject": None,
                "catalogus": expected_zaaktype_catalogus_url,
                "statustypen": [
                    {
                        "url": self._format_url(reverse(statustype)),
                        "omschrijving": statustype.statustype_omschrijving,
                        "omschrijvingGeneriek": "",
                        "statustekst": "",
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "volgnummer": statustype.statustypevolgnummer,
                        "isEindstatus": True,
                        "informeren": False,
                        "doorlooptijd": None,
                        "toelichting": None,
                        "checklistitemStatustype": [],
                        "catalogus": expected_zaaktype_catalogus_url,
                        "eigenschappen": [],
                        "zaakobjecttypen": [],
                        "beginGeldigheid": None,
                        "eindeGeldigheid": None,
                        "beginObject": None,
                        "eindeObject": None,
                    },
                ],
                "resultaattypen": [
                    {
                        "url": self._format_url(reverse(resultaattype)),
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "omschrijving": resultaattype.omschrijving,
                        "resultaattypeomschrijving": resultaattype.resultaattypeomschrijving,
                        "omschrijvingGeneriek": resultaattype.omschrijving_generiek,
                        "selectielijstklasse": resultaattype.selectielijstklasse,
                        "toelichting": resultaattype.toelichting,
                        "archiefnominatie": resultaattype.archiefnominatie,
                        "archiefactietermijn": "P10Y",
                        "brondatumArchiefprocedure": {
                            "afleidingswijze": "afgehandeld",
                            "datumkenmerk": "",
                            "einddatumBekend": False,
                            "objecttype": "",
                            "registratie": "",
                            "procestermijn": None,
                        },
                        "procesobjectaard": "",
                        "indicatieSpecifiek": None,
                        "procestermijn": None,
                        "catalogus": expected_zaaktype_catalogus_url,
                        "besluittypen": [],
                        "besluittypeOmschrijving": [],
                        "informatieobjecttypen": [],
                        "informatieobjecttypeOmschrijving": [],
                        "beginGeldigheid": None,
                        "eindeGeldigheid": None,
                        "beginObject": None,
                        "eindeObject": None,
                    },
                ],
                "eigenschappen": [
                    {
                        "url": self._format_url(reverse(eigenschaptype)),
                        "naam": eigenschaptype.eigenschapnaam,
                        "definitie": eigenschaptype.definitie,
                        "specificatie": {
                            "groep": "groep",
                            "formaat": "tekst",
                            "lengte": "20",
                            "kardinaliteit": "1",
                            "waardenverzameling": [],
                        },
                        "toelichting": eigenschaptype.toelichting,
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "catalogus": expected_zaaktype_catalogus_url,
                        "statustype": None,
                        "beginGeldigheid": None,
                        "eindeGeldigheid": None,
                        "beginObject": None,
                        "eindeObject": None,
                    },
                ],
                "informatieobjecttypen": [
                    {
                        "url": self._format_url(reverse(zaaktypeinformatieobjecttype)),
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "informatieobjecttype": self._format_url(
                            reverse(zaaktypeinformatieobjecttype.informatieobjecttype)
                        ),
                        "volgnummer": zaaktypeinformatieobjecttype.volgnummer,
                        "richting": zaaktypeinformatieobjecttype.richting.value,
                        "statustype": None,
                        "catalogus": expected_zaaktype_catalogus_url,
                    },
                ],
                "roltypen": [
                    {
                        "url": self._format_url(reverse(roltype)),
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "omschrijving": roltype.omschrijving,
                        "omschrijvingGeneriek": roltype.omschrijving_generiek,
                        "catalogus": expected_zaaktype_catalogus_url,
                        "beginGeldigheid": None,
                        "eindeGeldigheid": None,
                        "beginObject": None,
                        "eindeObject": None,
                    },
                ],
                "besluittypen": [],
                "deelzaaktypen": [],
                "gerelateerdeZaaktypen": [],
                "zaakobjecttypen": [
                    {
                        "url": self._format_url(reverse(zaakobjecttype)),
                        "anderObjecttype": zaakobjecttype.ander_objecttype,
                        "objecttype": zaakobjecttype.objecttype,
                        "relatieOmschrijving": zaakobjecttype.relatie_omschrijving,
                        "zaaktype": self._format_url(reverse(zaaktype)),
                        "zaaktypeIdentificatie": zaaktype.identificatie,
                        "resultaattypen": [],
                        "statustype": None,
                        "catalogus": expected_zaaktype_catalogus_url,
                        "beginGeldigheid": None,
                        "eindeGeldigheid": None,
                        "beginObject": None,
                        "eindeObject": None,
                    },
                ],
            },
            "registratiedatum": zaak.registratiedatum.isoformat(),
            "verantwoordelijkeOrganisatie": zaak.verantwoordelijke_organisatie,
            "startdatum": zaak.startdatum.isoformat(),
            "einddatum": zaak.einddatum,
            "einddatumGepland": zaak.einddatum_gepland,
            "uiterlijkeEinddatumAfdoening": zaak.uiterlijke_einddatum_afdoening,
            "publicatiedatum": zaak.publicatiedatum,
            "laatstGemuteerd": self._format_dt(zaak.laatst_gemuteerd),
            "laatstGeopend": zaak.laatst_geopend,
            "communicatiekanaal": zaak.communicatiekanaal,
            "communicatiekanaalNaam": zaak.communicatiekanaal_naam,
            "productenOfDiensten": zaak.producten_of_diensten,
            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            "betalingsindicatie": zaak.betalingsindicatie,
            "betalingsindicatieWeergave": "",
            "laatsteBetaaldatum": None,
            "zaakgeometrie": None,
            "verlenging": None,
            "opschorting": {
                "indicatie": False,
                "eerdereOpschorting": False,
                "reden": "",
            },
            "selectielijstklasse": zaak.selectielijstklasse,
            "hoofdzaak": None,
            "deelzaken": [],
            "relevanteAndereZaken": [],
            "gerelateerdeZaken": [],
            "eigenschappen": [
                {
                    "url": self._format_url(
                        reverse(
                            zaakeigenschaap,
                            kwargs={
                                "zaak_uuid": zaak.uuid,
                                "uuid": zaakeigenschaap.uuid,
                            },
                        )
                    ),
                    "uuid": str(zaakeigenschaap.uuid),
                    "zaak": expected_zaak_url,
                    "eigenschap": self._format_url(reverse(eigenschaptype)),
                    "naam": zaakeigenschaap._naam,
                    "waarde": zaakeigenschaap.waarde,
                },
            ],
            "rollen": [
                {
                    "url": self._format_url(reverse(rol)),
                    "uuid": str(rol.uuid),
                    "zaak": expected_zaak_url,
                    "betrokkene": rol.betrokkene,
                    "betrokkeneType": rol.betrokkene_type.value,
                    "afwijkendeNaamBetrokkene": rol.afwijkende_naam_betrokkene,
                    "roltype": self._format_url(reverse(roltype)),
                    "omschrijving": rol.omschrijving,
                    "omschrijvingGeneriek": rol.omschrijving_generiek.value,
                    "roltoelichting": rol.roltoelichting,
                    "registratiedatum": self._format_dt(rol.registratiedatum),
                    "indicatieMachtiging": rol.indicatie_machtiging,
                    "contactpersoonRol": {
                        "emailadres": "",
                        "functie": "",
                        "telefoonnummer": "",
                        "naam": "",
                    },
                    "statussen": [],
                    "beginGeldigheid": None,
                    "eindeGeldigheid": None,
                    "betrokkeneIdentificatie": {
                        "identificatie": "OE1",
                        "naam": "",
                        "isGehuisvestIn": "",
                    },
                },
            ],
            "status": {
                "url": self._format_url(reverse(zaakstatus)),
                "uuid": str(zaakstatus.uuid),
                "zaak": expected_zaak_url,
                "statustype": self._format_url(reverse(statustype)),
                "datumStatusGezet": self._format_dt(zaakstatus.datum_status_gezet),
                "statustoelichting": zaakstatus.statustoelichting,
                "indicatieLaatstGezetteStatus": True,
                "gezetdoor": None,
                "zaakinformatieobjecten": [],
                "substatussen": [
                    {
                        "url": self._format_url(reverse(substatus)),
                        "uuid": str(substatus.uuid),
                        "zaak": expected_zaak_url,
                        "status": self._format_url(reverse(zaakstatus)),
                        "omschrijving": substatus.omschrijving,
                        "tijdstip": self._format_dt(substatus.tijdstip),
                        "doelgroep": substatus.doelgroep.value,
                    }
                ],
            },
            "zaakinformatieobjecten": [
                {
                    "url": self._format_url(reverse(zaakinformatieobject)),
                    "uuid": str(zaakinformatieobject.uuid),
                    "informatieobject": self._format_url(
                        reverse(
                            "documenten:enkelvoudiginformatieobject-detail",
                            kwargs={
                                "uuid": zaakinformatieobject.informatieobject.latest_version.uuid
                            },
                        )
                    ),
                    "zaak": expected_zaak_url,
                    "aardRelatieWeergave": "Hoort bij, omgekeerd: kent",
                    "titel": zaakinformatieobject.titel,
                    "beschrijving": zaakinformatieobject.beschrijving,
                    "registratiedatum": self._format_dt(
                        zaakinformatieobject.registratiedatum
                    ),
                    "vernietigingsdatum": zaakinformatieobject.vernietigingsdatum,
                    "status": None,
                },
            ],
            "zaakobjecten": [
                {
                    "url": self._format_url(reverse(zaakobject)),
                    "uuid": str(zaakobject.uuid),
                    "zaak": expected_zaak_url,
                    "object": zaakobject.object,
                    "zaakobjecttype": None,
                    "objectType": zaakobject.object_type.value,
                    "objectTypeOverige": "",
                    "objectTypeOverigeDefinitie": None,
                    "relatieomschrijving": zaakobject.relatieomschrijving,
                },
            ],
            "kenmerken": [],
            "archiefnominatie": None,
            "archiefstatus": "nog_te_archiveren",
            "archiefactiedatum": None,
            "resultaat": {
                "url": self._format_url(reverse(resultaat)),
                "uuid": str(resultaat.uuid),
                "zaak": expected_zaak_url,
                "resultaattype": self._format_url(reverse(resultaattype)),
                "toelichting": resultaat.toelichting,
            },
            "opdrachtgevendeOrganisatie": "",
            "processobjectaard": "",
            "startdatumBewaartermijn": None,
            "processobject": {
                "datumkenmerk": "",
                "identificatie": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluiten": [
                {
                    "url": self._format_url(
                        reverse("zaken:besluit-detail", kwargs={"uuid": besluit.uuid}),
                    ),
                    "identificatie": besluit.identificatie,
                    "verantwoordelijkeOrganisatie": besluit.verantwoordelijke_organisatie,
                    "besluittype": self._format_url(
                        reverse(
                            "catalogi:besluittype-detail",
                            kwargs={"uuid": besluit.besluittype.uuid},
                        )
                    ),
                    "zaak": expected_zaak_url,
                    "datum": self._format_date(besluit.datum),
                    "toelichting": "",
                    "bestuursorgaan": "",
                    "ingangsdatum": self._format_date(besluit.ingangsdatum),
                    "vervaldatum": None,
                    "vervalreden": "",
                    "vervalredenWeergave": "",
                    "publicatiedatum": None,
                    "verzenddatum": None,
                    "uiterlijkeReactiedatum": None,
                }
            ],
            "statussen": [
                {
                    "url": self._format_url(reverse(zaakstatus)),
                    "uuid": str(zaakstatus.uuid),
                    "zaak": expected_zaak_url,
                    "statustype": self._format_url(reverse(statustype)),
                    "datumStatusGezet": self._format_dt(zaakstatus.datum_status_gezet),
                    "statustoelichting": zaakstatus.statustoelichting,
                    "indicatieLaatstGezetteStatus": True,
                    "gezetdoor": None,
                    "zaakinformatieobjecten": [],
                    "substatussen": [
                        {
                            "url": self._format_url(reverse(substatus)),
                            "uuid": str(substatus.uuid),
                            "zaak": expected_zaak_url,
                            "status": self._format_url(reverse(zaakstatus)),
                            "omschrijving": substatus.omschrijving,
                            "tijdstip": self._format_dt(substatus.tijdstip),
                            "doelgroep": substatus.doelgroep.value,
                        }
                    ],
                },
            ],
            "zaakcontactmomenten": [
                {
                    "url": self._format_url(reverse(zaakcontactmoment)),
                    "uuid": str(zaakcontactmoment.uuid),
                    "zaak": expected_zaak_url,
                    "contactmoment": zaakcontactmoment.contactmoment,
                },
            ],
            "zaakverzoeken": [
                {
                    "url": self._format_url(reverse(zaakverzoek)),
                    "uuid": str(zaakverzoek.uuid),
                    "zaak": expected_zaak_url,
                    "verzoek": zaakverzoek.verzoek,
                },
            ],
            "zaaknotities": [
                {
                    "url": self._format_url(reverse(zaaknotitie)),
                    "onderwerp": zaaknotitie.onderwerp,
                    "tekst": zaaknotitie.tekst,
                    "aangemaaktDoor": zaaknotitie.aangemaakt_door,
                    "notitieType": zaaknotitie.notitie_type.value,
                    "status": zaaknotitie.status.value,
                    "aanmaakdatum": self._format_dt(zaaknotitie.aanmaakdatum),
                    "wijzigingsdatum": self._format_dt(zaaknotitie.wijzigingsdatum),
                    "gerelateerdAan": expected_zaak_url,
                },
            ],
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)

    def test_zaak_with_only_zaaktype(self):
        zaaktype = self.zaaktype
        zaak = self.zaak

        response = self.client.get(self.url, {}, **ZAAK_READ_KWARGS)
        response_data = response.json()
        expected_zaak_url = self._format_url(reverse(zaak))
        expected_zaaktype_catalogus_url = self._format_url(reverse(zaaktype.catalogus))

        # Assert zaak relations has no data
        for relation in (
            "eigenschappen",
            "besluiten",
            "rollen",
            "statussen",
            "zaakcontactmomenten",
            "zaakinformatieobjecten",
            "zaakobjecten",
            "zaakverzoeken",
            "zaaknotities",
        ):
            self.assertEqual(len(response_data[relation]), 0, relation)

        # Assert zaaktype relations has no data
        nested_zaaktype = response_data["zaaktype"]
        self.assertNotIn("_expand", nested_zaaktype)
        for relation in (
            "eigenschappen",
            "resultaattypen",
            "roltypen",
            "statustypen",
            "zaakobjecttypen",
            "informatieobjecttypen",
        ):
            self.assertEqual(len(nested_zaaktype[relation]), 0, relation)

        expected_response = {
            "url": expected_zaak_url,
            "uuid": str(zaak.uuid),
            "identificatie": zaak.identificatie,
            "bronorganisatie": zaak.bronorganisatie,
            "omschrijving": zaak.omschrijving,
            "toelichting": "",
            "zaaktype": {
                "url": self._format_url(reverse(zaaktype)),
                "identificatie": zaaktype.identificatie,
                "omschrijving": zaaktype.zaaktype_omschrijving,
                "omschrijvingGeneriek": "",
                "vertrouwelijkheidaanduiding": "",
                "doel": zaaktype.doel,
                "aanleiding": zaaktype.aanleiding,
                "toelichting": "",
                "indicatieInternOfExtern": zaaktype.indicatie_intern_of_extern,
                "handelingInitiator": zaaktype.handeling_initiator,
                "onderwerp": zaaktype.onderwerp,
                "handelingBehandelaar": zaaktype.handeling_behandelaar,
                "doorlooptijd": "P30D",
                "servicenorm": None,
                "opschortingEnAanhoudingMogelijk": zaaktype.opschorting_en_aanhouding_mogelijk,
                "verlengingMogelijk": zaaktype.verlenging_mogelijk,
                "verlengingstermijn": None,
                "trefwoorden": [],
                "publicatieIndicatie": zaaktype.publicatie_indicatie,
                "publicatietekst": zaaktype.publicatietekst,
                "verantwoordingsrelatie": zaaktype.verantwoordingsrelatie,
                "productenOfDiensten": zaaktype.producten_of_diensten,
                "selectielijstProcestype": zaaktype.selectielijst_procestype,
                "referentieproces": {
                    "naam": zaaktype.referentieproces_naam,
                    "link": "",
                },
                "concept": zaaktype.concept,
                "verantwoordelijke": zaaktype.verantwoordelijke,
                "broncatalogus": {"url": "", "domein": "", "rsin": ""},
                "bronzaaktype": {
                    "url": "",
                    "identificatie": "",
                    "omschrijving": "",
                },
                "beginGeldigheid": self._format_date(zaaktype.datum_begin_geldigheid),
                "eindeGeldigheid": None,
                "versiedatum": self._format_date(zaaktype.versiedatum),
                "beginObject": self._format_date(zaaktype.datum_begin_geldigheid),
                "eindeObject": None,
                "catalogus": expected_zaaktype_catalogus_url,
                "statustypen": [],
                "resultaattypen": [],
                "eigenschappen": [],
                "informatieobjecttypen": [],
                "roltypen": [],
                "besluittypen": [],
                "deelzaaktypen": [],
                "gerelateerdeZaaktypen": [],
                "zaakobjecttypen": [],
            },
            "registratiedatum": zaak.registratiedatum.isoformat(),
            "verantwoordelijkeOrganisatie": zaak.verantwoordelijke_organisatie,
            "startdatum": zaak.startdatum.isoformat(),
            "einddatum": zaak.einddatum,
            "einddatumGepland": zaak.einddatum_gepland,
            "uiterlijkeEinddatumAfdoening": zaak.uiterlijke_einddatum_afdoening,
            "publicatiedatum": zaak.publicatiedatum,
            "laatstGemuteerd": self._format_dt(zaak.laatst_gemuteerd),
            "laatstGeopend": zaak.laatst_geopend,
            "communicatiekanaal": zaak.communicatiekanaal,
            "communicatiekanaalNaam": zaak.communicatiekanaal_naam,
            "productenOfDiensten": zaak.producten_of_diensten,
            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            "betalingsindicatie": zaak.betalingsindicatie,
            "betalingsindicatieWeergave": "",
            "laatsteBetaaldatum": None,
            "zaakgeometrie": None,
            "verlenging": None,
            "opschorting": {
                "indicatie": False,
                "eerdereOpschorting": False,
                "reden": "",
            },
            "selectielijstklasse": zaak.selectielijstklasse,
            "hoofdzaak": None,
            "deelzaken": [],
            "relevanteAndereZaken": [],
            "gerelateerdeZaken": [],
            "eigenschappen": [],
            "rollen": [],
            "status": None,
            "zaakinformatieobjecten": [],
            "zaakobjecten": [],
            "kenmerken": [],
            "archiefnominatie": None,
            "archiefstatus": "nog_te_archiveren",
            "archiefactiedatum": None,
            "resultaat": None,
            "opdrachtgevendeOrganisatie": "",
            "processobjectaard": "",
            "startdatumBewaartermijn": None,
            "processobject": {
                "datumkenmerk": "",
                "identificatie": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluiten": [],
            "statussen": [],
            "zaakcontactmomenten": [],
            "zaakverzoeken": [],
            "zaaknotities": [],
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_data, expected_response)

    def test_only_get_is_allowed(self):
        zaak = ZaakFactory()
        url = reverse("zaken:zaakinzage", kwargs={"uuid": zaak.uuid})

        response = self.client.post(url, {}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_without_uuid_is_not_allowed(self):
        """Create test without uuid must return 404"""
        url = reverse(
            "zaken:zaakinzage",
            kwargs={"uuid": uuid.uuid4(), "version": "1"},
        ).rsplit("/", 1)[0]  # Create url with a uuid and remove uuid before GET request
        response = self.client.get(url, {}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_authentication_should_fail(self):
        zaak = ZaakFactory()

        self.client.logout()  # remove JWT token

        url = reverse("zaken:zaakinzage", kwargs={"uuid": zaak.uuid})

        response = self.client.get(url, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
