# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.tests import get_validation_errors

from openzaak.components.besluiten.api.audits import AUDIT_BRC
from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.catalogi.constants import (
    InternExtern,
    SelectielijstKlasseProcestermijn as Procestermijn,
)
from openzaak.components.catalogi.models import ZaakTypeInformatieObjectType
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    EigenschapFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakObjectTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.api.audits import AUDIT_ZRC
from openzaak.components.zaken.models import Zaak, ZaakEigenschap
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.components.zaken.tests.utils import ZAAK_WRITE_KWARGS
from openzaak.selectielijst.tests.mixins import SelectieLijstMixin
from openzaak.tests.utils import JWTAuthMixin, patch_resource_validator
from openzaak.utils.urls import reverse


class BesluitenApiDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.besluit = BesluitFactory.create(for_zaak=True)
        self.besluitInformatieObject = BesluitInformatieObjectFactory.create()

    def test_deprecated_besluiten_api_response(self):
        with self.subTest("besluit"):
            url = reverse(self.besluit, namespace="besluiten")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("besluiten/api/v1/besluiten", response.data["url"])
            self.assertIn("catalogi/api/v1/besluittypen", response.data["besluittype"])
            self.assertIn("zaken/api/v1/zaken", response.data["zaak"])

        with self.subTest("besluitinformatieobject"):
            url = reverse(self.besluitInformatieObject, namespace="besluiten")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(
                "besluiten/api/v1/besluitinformatieobjecten", response.data["url"]
            )
            self.assertIn("besluiten/api/v1/besluiten", response.data["besluit"])
            self.assertIn(
                "documenten/api/v1/enkelvoudiginformatieobjecten",
                response.data["informatieobject"],
            )

    def test_zaken_api_response(self):
        with self.subTest("besluit"):
            url = reverse(self.besluit, namespace="zaken")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("zaken/api/v1/besluiten", response.data["url"])
            self.assertIn("zaken/api/v1/besluittypen", response.data["besluittype"])
            self.assertIn("zaken/api/v1/zaken", response.data["zaak"])

        with self.subTest("besluitinformatieobject"):
            url = reverse(self.besluitInformatieObject, namespace="zaken")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(
                "zaken/api/v1/besluitinformatieobjecten", response.data["url"]
            )
            self.assertIn("zaken/api/v1/besluiten", response.data["besluit"])
            self.assertIn(
                "documenten/api/v1/enkelvoudiginformatieobjecten",
                response.data["informatieobject"],
            )

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("besluiten:besluit-list"), "/besluiten/api/v1/besluiten"
        )
        self.assertEqual(
            reverse("besluiten:besluit-detail", kwargs={"uuid": 1}),
            "/besluiten/api/v1/besluiten/1",
        )
        self.assertEqual(
            reverse("besluiten:besluitinformatieobject-list"),
            "/besluiten/api/v1/besluitinformatieobjecten",
        )
        self.assertEqual(
            reverse("besluiten:besluitinformatieobject-detail", kwargs={"uuid": 1}),
            "/besluiten/api/v1/besluitinformatieobjecten/1",
        )
        self.assertEqual(
            reverse("besluiten:verwerkbesluit-list"),
            "/besluiten/api/v1/besluit_verwerken",
        )
        self.assertEqual(
            reverse("besluiten:audittrail-list", kwargs={"besluit_uuid": 1}),
            "/besluiten/api/v1/besluiten/1/audittrail",
        )

    def test_new_paths(self):
        self.assertEqual(reverse("zaken:besluit-list"), "/zaken/api/v1/besluiten")
        self.assertEqual(
            reverse("zaken:besluit-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/besluiten/1",
        )
        self.assertEqual(
            reverse("zaken:besluitinformatieobject-list"),
            "/zaken/api/v1/besluitinformatieobjecten",
        )
        self.assertEqual(
            reverse("zaken:besluitinformatieobject-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/besluitinformatieobjecten/1",
        )
        self.assertEqual(
            reverse("zaken:verwerkbesluit-list"), "/zaken/api/v1/besluit_verwerken"
        )

        # audittrails
        self.assertEqual(
            reverse("zaken:audittrail-list", kwargs={"besluit_uuid": 1}),
            "/zaken/api/v1/besluiten/1/audittrail",
        )
        self.assertEqual(
            reverse("zaken:audittrail-list", kwargs={"zaak_uuid": 1}),
            "/zaken/api/v1/zaken/1/audittrail",
        )

    def test_create_bio_in_besluiten_with_zaken_url(self):
        url = reverse(BesluitInformatieObject, namespace="besluiten")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{reverse(besluit, namespace='zaken')}",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json()["besluit"],
            f"http://testserver{reverse(besluit, namespace='besluiten')}",
        )

    def test_create_bio_in_zaken_with_besluiten_url(self):
        url = reverse(BesluitInformatieObject, namespace="zaken")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{reverse(besluit, namespace='besluiten')}"
                "",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json()["besluit"],
            f"http://testserver{reverse(besluit, namespace='zaken')}",
        )

    def test_create_bio_in_zaken_with_non_existent_namespace(self):
        """
        resolve_path in permission check returns ObjectNotFound
        """
        url = reverse(BesluitInformatieObject, namespace="zaken")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver/blabla/api/v1/besluiten/{besluit.uuid}",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "besluit")
        self.assertEqual(error["code"], "object-does-not-exist")

    def test_create_zaakbesluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        besluit.besluittype.zaaktypen.add(zaak.zaaktype)

        with self.subTest("both in zaken namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver{reverse(besluit, namespace='zaken')}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("besluit namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("non existent namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver/blabla/api/v1/besluiten/{besluit.uuid}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BesluitAudittrailTests(JWTAuthMixin, APITestCase):
    """
    Urls are stored in auditrail itself and won't change when changing namespace
    """

    heeft_alle_autorisaties = True
    maxDiff = None

    def setUp(self):
        super().setUp()

        besluittype = BesluitTypeFactory.create(concept=False)
        self.besluittype_url = (
            f"http://testserver{reverse(besluittype, namespace='catalogi')}"
        )
        self.data = {
            "besluittype": self.besluittype_url,
            "verantwoordelijke_organisatie": "517439943",
            "datum": "2026-05-05",
            "ingangsdatum": "2026-05-05",
            "toelichting": "desc",
        }

    def test_audittrail_in_besluiten_api(self):
        besluiten_url = reverse("besluiten:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        besluit = Besluit.objects.get()
        besluit_url = reverse(besluit, namespace="besluiten")

        with self.subTest("audittrail model"):
            self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}")
            self.assertEqual(audittrail.resource, "besluit")
            self.assertEqual(audittrail.resource_url, f"http://testserver{besluit_url}")
            self.assertEqual(
                audittrail.resource_weergave, besluit.unique_representation()
            )

        with self.subTest("fetch from besluiten api"):
            url = reverse(
                "besluiten:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{besluit_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{besluit_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{besluit_url}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

        with self.subTest("fetch from zaken api"):
            url = reverse(
                "zaken:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{besluit_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{besluit_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{besluit_url}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

    def test_audittrail_in_zaken_api(self):
        besluiten_url = reverse("zaken:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        besluit = Besluit.objects.get()

        with self.subTest("audittrail model"):
            self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(
                audittrail.hoofd_object,
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(audittrail.resource, "besluit")
            self.assertEqual(
                audittrail.resource_url,
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                audittrail.resource_weergave, besluit.unique_representation()
            )

        with self.subTest("fetch from besluiten api"):
            url = reverse(
                "besluiten:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(
                data["hoofdObject"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["resourceUrl"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

        with self.subTest("fetch from zaken api"):
            url = reverse(
                "zaken:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(
                data["hoofdObject"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["resourceUrl"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

    def test_created_in_brc_updated_in_zrc(self):
        besluiten_url = reverse("besluiten:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        besluit = Besluit.objects.get()

        besluit_url = reverse(besluit, namespace="zaken")
        response = self.client.patch(besluit_url, {"toelichting": "asc"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(AuditTrail.objects.count(), 2)
        self.assertEqual(len(besluit.audittrail), 2)

        create_trail = AuditTrail.objects.first()
        update_trail = AuditTrail.objects.last()

        self.assertEqual(create_trail.actie, "create")
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.hoofd_object)
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.resource_url)
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.nieuw["url"])

        self.assertEqual(update_trail.actie, "partial_update")
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.hoofd_object)
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.resource_url)
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.oud["url"])
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.nieuw["url"])


@freeze_time("2026-05-05T12:00:00")
class ZaakAudittrailTests(JWTAuthMixin, APITestCase):
    """
    Urls are stored in auditrail itself and won't change when changing namespace
    """

    heeft_alle_autorisaties = True
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.zaaktype = ZaakTypeFactory.create(concept=False)
        self.data = {
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2026-05-05",
            "startdatum": "2026-05-05",
            "toelichting": "desc",
        }

    def test_audittrail_with_zaaktype_in_catalogi_namespace(self):
        zaken_url = reverse("zaken:zaak-list")
        zaaktype_url = (
            f"http://testserver{reverse(self.zaaktype, namespace='catalogi')}"
        )

        response = self.client.post(
            zaken_url, {**self.data, "zaaktype": zaaktype_url}, **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        zaak = Zaak.objects.get()
        zaak_url = reverse(zaak, namespace="zaken")

        with self.subTest("audittrail model"):
            self.assertEqual(audittrail.bron, AUDIT_ZRC.component_name)
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}")
            self.assertEqual(audittrail.resource, "zaak")
            self.assertEqual(audittrail.resource_url, f"http://testserver{zaak_url}")
            self.assertEqual(audittrail.resource_weergave, zaak.unique_representation())
            self.assertEqual(
                audittrail.nieuw["zaaktype"],
                f"http://testserver{reverse(self.zaaktype, namespace='zaken')}",
            )

        with self.subTest("fetch from zaken api"):
            url = reverse("zaken:audittrail-list", kwargs={"zaak_uuid": zaak.uuid})

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_ZRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{zaak_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{zaak_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{zaak_url}",
                        "uuid": str(zaak.uuid),
                        "rollen": [],
                        "status": None,
                        "zaaktype": f"http://testserver{reverse(self.zaaktype, namespace='zaken')}",
                        "deelzaken": [],
                        "einddatum": None,
                        "hoofdzaak": None,
                        "kenmerken": [],
                        "resultaat": None,
                        "startdatum": "2026-05-05",
                        "verlenging": None,
                        "opschorting": {
                            "reden": "",
                            "indicatie": False,
                            "eerdereOpschorting": False,
                        },
                        "toelichting": "desc",
                        "omschrijving": "",
                        "zaakobjecten": [],
                        "archiefstatus": "nog_te_archiveren",
                        "eigenschappen": [],
                        "identificatie": "ZAAK-2026-0000000001",
                        "processobject": {
                            "objecttype": "",
                            "registratie": "",
                            "datumkenmerk": "",
                            "identificatie": "",
                        },
                        "zaakgeometrie": None,
                        "laatstGeopend": None,
                        "bronorganisatie": "517439943",
                        "publicatiedatum": None,
                        "archiefnominatie": None,
                        "laatstGemuteerd": "2026-05-05T12:00:00Z",
                        "registratiedatum": "2026-05-05",
                        "archiefactiedatum": None,
                        "einddatumGepland": None,
                        "processobjectaard": "",
                        "betalingsindicatie": "",
                        "communicatiekanaal": "",
                        "gerelateerdeZaken": [],
                        "laatsteBetaaldatum": None,
                        "selectielijstklasse": "",
                        "productenOfDiensten": [],
                        "relevanteAndereZaken": [],
                        "zaakinformatieobjecten": [],
                        "communicatiekanaalNaam": "",
                        "startdatumBewaartermijn": None,
                        "betalingsindicatieWeergave": "",
                        "opdrachtgevendeOrganisatie": "",
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "verantwoordelijkeOrganisatie": "517439943",
                        "uiterlijkeEinddatumAfdoening": "2026-06-04",
                    },
                },
            )

    def test_audittrail_with_zaaktype_in_zaken_namespace(self):
        zaken_url = reverse("zaken:zaak-list")
        zaaktype_url = f"http://testserver{reverse(self.zaaktype, namespace='zaken')}"

        response = self.client.post(
            zaken_url, {**self.data, "zaaktype": zaaktype_url}, **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        zaak = Zaak.objects.get()
        zaak_url = reverse(zaak, namespace="zaken")

        with self.subTest("audittrail model"):
            self.assertEqual(audittrail.bron, AUDIT_ZRC.component_name)
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(audittrail.hoofd_object, f"http://testserver{zaak_url}")
            self.assertEqual(audittrail.resource, "zaak")
            self.assertEqual(audittrail.resource_url, f"http://testserver{zaak_url}")
            self.assertEqual(audittrail.resource_weergave, zaak.unique_representation())
            self.assertEqual(
                audittrail.nieuw["zaaktype"],
                f"http://testserver{reverse(self.zaaktype, namespace='zaken')}",
            )

        with self.subTest("fetch from zaken api"):
            url = reverse("zaken:audittrail-list", kwargs={"zaak_uuid": zaak.uuid})

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_ZRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{zaak_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{zaak_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{zaak_url}",
                        "uuid": str(zaak.uuid),
                        "rollen": [],
                        "status": None,
                        "zaaktype": f"http://testserver{reverse(self.zaaktype, namespace='zaken')}",
                        "deelzaken": [],
                        "einddatum": None,
                        "hoofdzaak": None,
                        "kenmerken": [],
                        "resultaat": None,
                        "startdatum": "2026-05-05",
                        "verlenging": None,
                        "opschorting": {
                            "reden": "",
                            "indicatie": False,
                            "eerdereOpschorting": False,
                        },
                        "toelichting": "desc",
                        "omschrijving": "",
                        "zaakobjecten": [],
                        "archiefstatus": "nog_te_archiveren",
                        "eigenschappen": [],
                        "identificatie": "ZAAK-2026-0000000001",
                        "processobject": {
                            "objecttype": "",
                            "registratie": "",
                            "datumkenmerk": "",
                            "identificatie": "",
                        },
                        "zaakgeometrie": None,
                        "laatstGeopend": None,
                        "bronorganisatie": "517439943",
                        "publicatiedatum": None,
                        "archiefnominatie": None,
                        "laatstGemuteerd": "2026-05-05T12:00:00Z",
                        "registratiedatum": "2026-05-05",
                        "archiefactiedatum": None,
                        "einddatumGepland": None,
                        "processobjectaard": "",
                        "betalingsindicatie": "",
                        "communicatiekanaal": "",
                        "gerelateerdeZaken": [],
                        "laatsteBetaaldatum": None,
                        "selectielijstklasse": "",
                        "productenOfDiensten": [],
                        "relevanteAndereZaken": [],
                        "zaakinformatieobjecten": [],
                        "communicatiekanaalNaam": "",
                        "startdatumBewaartermijn": None,
                        "betalingsindicatieWeergave": "",
                        "opdrachtgevendeOrganisatie": "",
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "verantwoordelijkeOrganisatie": "517439943",
                        "uiterlijkeEinddatumAfdoening": "2026-06-04",
                    },
                },
            )

    def test_created_with_catalogi_zaaktype_updated_with_zaken_zaaktype(self):
        zaken_url = reverse("zaken:zaak-list")
        zaaktype_url = (
            f"http://testserver{reverse(self.zaaktype, namespace='catalogi')}"
        )

        response = self.client.post(
            zaken_url, {**self.data, "zaaktype": zaaktype_url}, **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        zaak = Zaak.objects.get()

        zaak_url = reverse(zaak, namespace="zaken")
        response = self.client.patch(
            zaak_url,
            {
                "zaaktype": f"http://testserver{reverse(self.zaaktype, namespace='zaken')}",
                "toelichting": "asc",
            },
            **ZAAK_WRITE_KWARGS,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(AuditTrail.objects.count(), 2)

        create_trail = AuditTrail.objects.first()
        update_trail = AuditTrail.objects.last()

        self.assertEqual(create_trail.actie, "create")
        self.assertIn("/zaken/api/v1/zaken/", create_trail.hoofd_object)
        self.assertIn("/zaken/api/v1/zaken/", create_trail.resource_url)
        self.assertIn("/zaken/api/v1/zaaktypen/", create_trail.nieuw["zaaktype"])

        self.assertEqual(update_trail.actie, "partial_update")
        self.assertIn("/zaken/api/v1/zaken/", update_trail.hoofd_object)
        self.assertIn("/zaken/api/v1/zaken/", update_trail.resource_url)
        self.assertIn("/zaken/api/v1/zaaktypen/", update_trail.oud["zaaktype"])
        self.assertIn("/zaken/api/v1/zaaktypen/", update_trail.nieuw["zaaktype"])


class InformatieObjectTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.iot = InformatieObjectTypeFactory.create(concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.iot, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/informatieobjecttype", response.data["url"])
        self.assertIn("catalogi/api/v1/catalogus", response.data["catalogus"])

    def test_documenten_api_response(self):
        url = reverse(self.iot, namespace="documenten")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("documenten/api/v1/informatieobjecttype", response.data["url"])
        self.assertIn("zaken/api/v1/catalogus", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:informatieobjecttype-list"),
            "/catalogi/api/v1/informatieobjecttypen",
        )
        self.assertEqual(
            reverse("catalogi:informatieobjecttype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/informatieobjecttypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("documenten:informatieobjecttype-list"),
            "/documenten/api/v1/informatieobjecttypen",
        )
        self.assertEqual(
            reverse("documenten:informatieobjecttype-detail", kwargs={"uuid": 1}),
            "/documenten/api/v1/informatieobjecttypen/1",
        )

    def test_create_eio_with_catalogi_url(self):
        url = reverse(EnkelvoudigInformatieObject, namespace="documenten")

        response = self.client.post(
            url,
            {
                "informatieobjecttype": f"http://testserver{reverse(self.iot, namespace='catalogi')}",
                "bronorganisatie": "517439943",
                "creatiedatum": "2026-05-05",
                "titel": "test",
                "auteur": "test",
                "taal": "nld",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(
            response.json()["informatieobjecttype"],
            f"http://testserver{reverse(self.iot, namespace='documenten')}",
        )

    def test_create_eio_with_documenten_url(self):
        url = reverse(EnkelvoudigInformatieObject, namespace="documenten")

        response = self.client.post(
            url,
            {
                "informatieobjecttype": f"http://testserver{reverse(self.iot, namespace='documenten')}",
                "bronorganisatie": "517439943",
                "creatiedatum": "2026-05-05",
                "titel": "test",
                "auteur": "test",
                "taal": "nld",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(
            response.json()["informatieobjecttype"],
            f"http://testserver{reverse(self.iot, namespace='documenten')}",
        )

    def test_create_ziot_with_catalogi_url(self):
        url = reverse(ZaakTypeInformatieObjectType, namespace="catalogi")
        zaaktype = ZaakTypeFactory.create(catalogus=self.iot.catalogus)

        response = self.client.post(
            url,
            {
                "informatieobjecttype": f"http://testserver{reverse(self.iot, namespace='catalogi')}",
                "zaaktype": f"http://testserver{reverse(zaaktype, namespace='catalogi')}",
                "volgnummer": 1,
                "richting": "inkomend",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(
            response.json()["informatieobjecttype"],
            f"http://testserver{reverse(self.iot, namespace='catalogi')}",
        )

    def test_create_ziot_with_documenten_url(self):
        url = reverse(ZaakTypeInformatieObjectType, namespace="catalogi")
        zaaktype = ZaakTypeFactory.create(catalogus=self.iot.catalogus)

        response = self.client.post(
            url,
            {
                "informatieobjecttype": f"http://testserver{reverse(self.iot, namespace='documenten')}",
                "zaaktype": f"http://testserver{reverse(zaaktype, namespace='catalogi')}",
                "volgnummer": 1,
                "richting": "inkomend",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(
            response.json()["informatieobjecttype"],
            f"http://testserver{reverse(self.iot, namespace='catalogi')}",
        )


class BesluitTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.bt = BesluitTypeFactory.create(concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.bt, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/besluittype", response.data["url"])
        self.assertIn("catalogi/api/v1/catalogus", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.bt, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/besluittype", response.data["url"])
        self.assertIn("zaken/api/v1/catalogus", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:besluittype-list"),
            "/catalogi/api/v1/besluittypen",
        )
        self.assertEqual(
            reverse("catalogi:besluittype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/besluittypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:besluittype-list"),
            "/zaken/api/v1/besluittypen",
        )
        self.assertEqual(
            reverse("zaken:besluittype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/besluittypen/1",
        )

    def test_create_besluit_with_namespaces(self):
        def create(b_namespace: str, bt_namespace: str):
            url = reverse(Besluit, namespace=b_namespace)

            response = self.client.post(
                url,
                {
                    "besluittype": f"http://testserver{reverse(self.bt, namespace=bt_namespace)}",
                    "verantwoordelijke_organisatie": "517439943",
                    "datum": "2026-05-05",
                    "ingangsdatum": "2026-05-05",
                    "toelichting": "desc",
                },
            )
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.json()
            )
            return response

        with self.subTest("besluit in zaken with zaken bt"):
            response = create("zaken", "zaken")
            self.assertEqual(
                response.json()["besluittype"],
                f"http://testserver{reverse(self.bt, namespace='zaken')}",
            )

        with self.subTest("besluit in zaken with catalogi bt"):
            response = create("zaken", "catalogi")
            self.assertEqual(
                response.json()["besluittype"],
                f"http://testserver{reverse(self.bt, namespace='zaken')}",
            )

        with self.subTest("besluit in besluiten with catalogi bt"):
            response = create("besluiten", "catalogi")
            self.assertEqual(
                response.json()["besluittype"],
                f"http://testserver{reverse(self.bt, namespace='catalogi')}",
            )

        with self.subTest("besluit in besluiten with zaken bt"):
            response = create("besluiten", "zaken")
            self.assertEqual(
                response.json()["besluittype"],
                f"http://testserver{reverse(self.bt, namespace='catalogi')}",
            )


class ZaakTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = ZaakTypeFactory.create(concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["url"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/zaaktypen", response.data["url"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:zaaktype-list"),
            "/catalogi/api/v1/zaaktypen",
        )
        self.assertEqual(
            reverse("catalogi:zaaktype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/zaaktypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:zaaktype-list"),
            "/zaken/api/v1/zaaktypen",
        )
        self.assertEqual(
            reverse("zaken:zaaktype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/zaaktypen/1",
        )

    def test_create_zaaktype_with_namespaces(self):
        catalogus = self.obj.catalogus
        besluittype = BesluitTypeFactory.create(catalogus=catalogus, concept=False)

        for i, (namespace, related_namespace) in enumerate(self.NAMESPACE_COMBINATIONS):
            with self.subTest(namespace=namespace, related_namespace=related_namespace):
                response = self.client.post(
                    reverse(f"{namespace}:zaaktype-list"),
                    {
                        "identificatie": f"ZAAKTYPE-{i}",
                        "doel": "some test",
                        "aanleiding": "some test",
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
                        "catalogus": f"http://testserver{reverse(catalogus, namespace=related_namespace)}",
                        "besluittypen": [
                            f"http://testserver{reverse(besluittype, namespace=related_namespace)}"
                        ],
                        "beginGeldigheid": "2018-01-01",
                        "versiedatum": "2018-01-01",
                        "verantwoordelijke": "063308836",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/zaaktypen", data["url"])
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(catalogus, namespace=namespace)}",
                )
                self.assertEqual(
                    data["besluittypen"],
                    [f"http://testserver{reverse(besluittype, namespace=namespace)}"],
                )

    def test_create_zaak_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(zaaktype_namespace=namespace):
                response = self.client.post(
                    reverse("zaken:zaak-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                        "bronorganisatie": "517439943",
                        "verantwoordelijkeOrganisatie": "517439943",
                        "registratiedatum": "2026-05-05",
                        "startdatum": "2026-05-05",
                    },
                    **ZAAK_WRITE_KWARGS,
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["zaaktype"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


class StatusTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = StatusTypeFactory.create(zaaktype__concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/statustypen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/statustypen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:statustype-list"),
            "/catalogi/api/v1/statustypen",
        )
        self.assertEqual(
            reverse("catalogi:statustype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/statustypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:statustype-list"),
            "/zaken/api/v1/statustypen",
        )
        self.assertEqual(
            reverse("zaken:statustype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/statustypen/1",
        )

    def test_create_statustype_with_namespaces(self):
        for namespace, zaaktype_namespace in self.NAMESPACE_COMBINATIONS:
            with self.subTest(
                namespace=namespace, zaaktype_namespace=zaaktype_namespace
            ):
                zaaktype = ZaakTypeFactory.create()
                response = self.client.post(
                    reverse(f"{namespace}:statustype-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "omschrijving": "Besluit genomen",
                        "omschrijvingGeneriek": "",
                        "statustekst": "",
                        "volgnummer": 1,
                        "beginGeldigheid": "2023-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/statustypen", data["url"])
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )

    def test_create_status_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(statustype_namespace=namespace):
                zaak = ZaakFactory.create(zaaktype=self.obj.zaaktype)
                StatusTypeFactory.create(zaaktype=self.obj.zaaktype)
                response = self.client.post(
                    reverse("zaken:status-list"),
                    {
                        "zaak": f"http://testserver{reverse(zaak, namespace='zaken')}",
                        "statustype": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "datumStatusGezet": "2026-05-05T00:00:00",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["statustype"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


class EigenschapDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = EigenschapFactory.create(zaaktype__concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/eigenschappen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/eigenschappen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:eigenschap-list"),
            "/catalogi/api/v1/eigenschappen",
        )
        self.assertEqual(
            reverse("catalogi:eigenschap-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/eigenschappen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:eigenschap-list"),
            "/zaken/api/v1/eigenschappen",
        )
        self.assertEqual(
            reverse("zaken:eigenschap-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/eigenschappen/1",
        )

    def test_create_eigenschap_with_namespaces(self):
        for namespace, zaaktype_namespace in self.NAMESPACE_COMBINATIONS:
            with self.subTest(
                namespace=namespace, zaaktype_namespace=zaaktype_namespace
            ):
                zaaktype = ZaakTypeFactory.create()
                response = self.client.post(
                    reverse(f"{namespace}:eigenschap-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "naam": "Beoogd product",
                        "definitie": "test",
                        "toelichting": "",
                        "specificatie": {
                            "groep": "test",
                            "formaat": "tekst",
                            "lengte": "5",
                            "kardinaliteit": "1",
                            "waardenverzameling": [],
                        },
                        "beginGeldigheid": "2023-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/eigenschappen", data["url"])
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )

    def test_create_zaakeigenschap_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(eigenschap_namespace=namespace):
                zaak = ZaakFactory.create(zaaktype=self.obj.zaaktype)
                response = self.client.post(
                    reverse(ZaakEigenschap, kwargs={"zaak_uuid": zaak.uuid}),
                    {
                        "zaak": f"http://testserver{reverse(zaak, namespace='zaken')}",
                        "eigenschap": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "waarde": "test",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["eigenschap"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class RolTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = RolTypeFactory.create(zaaktype__concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/roltypen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/roltypen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:roltype-list"),
            "/catalogi/api/v1/roltypen",
        )
        self.assertEqual(
            reverse("catalogi:roltype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/roltypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:roltype-list"),
            "/zaken/api/v1/roltypen",
        )
        self.assertEqual(
            reverse("zaken:roltype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/roltypen/1",
        )

    def test_create_roltype_with_namespaces(self):
        for namespace, zaaktype_namespace in self.NAMESPACE_COMBINATIONS:
            with self.subTest(
                namespace=namespace, zaaktype_namespace=zaaktype_namespace
            ):
                zaaktype = ZaakTypeFactory.create()
                response = self.client.post(
                    reverse(f"{namespace}:roltype-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "omschrijving": "Vergunningaanvrager",
                        "omschrijvingGeneriek": RolOmschrijving.initiator,
                        "beginGeldigheid": "2023-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/roltypen", data["url"])
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )

    def test_create_rol_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(roltype_namespace=namespace):
                zaak = ZaakFactory.create(zaaktype=self.obj.zaaktype)
                response = self.client.post(
                    reverse("zaken:rol-list"),
                    {
                        "zaak": f"http://testserver{reverse(zaak, namespace='zaken')}",
                        "roltype": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "betrokkene": "http://www.some-api.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                        "betrokkeneType": RolTypes.medewerker,
                        "roltoelichting": "foo",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["roltype"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


@override_settings(SOLO_CACHE=None)
class ResultaatTypeDeprecationTests(SelectieLijstMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    PROCESTYPE_URL = "http://referentielijsten.nl/procestypen/1234"
    SELECTIELIJSTKLASSE_URL = "https://selectielijst.openzaak.nl/api/v1/resultaten/1234"
    RESULTAATTYPEOMSCHRIJVING_URL = (
        "https://selectielijst.openzaak.nl/api/v1/omschrijving/1"
    )

    def setUp(self):
        super().setUp()
        self.obj = ResultaatTypeFactory.create(zaaktype__concept=False)

        self.requests_mocker.get(
            self.SELECTIELIJSTKLASSE_URL,
            json={
                "url": self.SELECTIELIJSTKLASSE_URL,
                "procesType": self.PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            },
        )
        self.requests_mocker.get(
            self.RESULTAATTYPEOMSCHRIJVING_URL, json={"omschrijving": "test"}
        )

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/resultaattypen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/resultaattypen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:resultaattype-list"),
            "/catalogi/api/v1/resultaattypen",
        )
        self.assertEqual(
            reverse("catalogi:resultaattype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/resultaattypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:resultaattype-list"),
            "/zaken/api/v1/resultaattypen",
        )
        self.assertEqual(
            reverse("zaken:resultaattype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/resultaattypen/1",
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch_resource_validator
    def test_create_resultaattype_with_namespaces(self, *mocks):
        for namespace, zaaktype_namespace in self.NAMESPACE_COMBINATIONS:
            with self.subTest(
                namespace=namespace, zaaktype_namespace=zaaktype_namespace
            ):
                zaaktype = ZaakTypeFactory.create(
                    selectielijst_procestype=self.PROCESTYPE_URL
                )
                response = self.client.post(
                    reverse(f"{namespace}:resultaattype-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "omschrijving": "illum",
                        "resultaattypeomschrijving": self.RESULTAATTYPEOMSCHRIJVING_URL,
                        "selectielijstklasse": self.SELECTIELIJSTKLASSE_URL,
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
                        "beginGeldigheid": "2023-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/resultaattypen", data["url"])
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )

    def test_create_resultaat_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(resultaattype_namespace=namespace):
                zaak = ZaakFactory.create(zaaktype=self.obj.zaaktype)
                response = self.client.post(
                    reverse("zaken:resultaat-list"),
                    {
                        "zaak": f"http://testserver{reverse(zaak, namespace='zaken')}",
                        "resultaattype": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "toelichting": "",
                    },
                    **ZAAK_WRITE_KWARGS,
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["resultaattype"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


class ZaakTypeInformatieObjectDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "catalogi/api/v1/zaaktype-informatieobjecttypen", response.data["url"]
        )
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn(
            "catalogi/api/v1/informatieobjecttypen",
            response.data["informatieobjecttype"],
        )
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "zaken/api/v1/zaaktype-informatieobjecttypen", response.data["url"]
        )
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn(
            "documenten/api/v1/informatieobjecttypen",
            response.data["informatieobjecttype"],
        )
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:zaaktypeinformatieobjecttype-list"),
            "/catalogi/api/v1/zaaktype-informatieobjecttypen",
        )
        self.assertEqual(
            reverse("catalogi:zaaktypeinformatieobjecttype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/zaaktype-informatieobjecttypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:zaaktypeinformatieobjecttype-list"),
            "/zaken/api/v1/zaaktype-informatieobjecttypen",
        )
        self.assertEqual(
            reverse("zaken:zaaktypeinformatieobjecttype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/zaaktype-informatieobjecttypen/1",
        )

    def test_create_zaaktypeinformatieobjecttype_with_namespaces(self):
        combinations = [
            (namespace, related_namespace, iot_namespace)
            for namespace, related_namespace in self.NAMESPACE_COMBINATIONS
            for iot_namespace in ("catalogi", "documenten")
        ]
        for namespace, zaaktype_namespace, iot_namespace in combinations:
            with self.subTest(
                namespace=namespace,
                zaaktype_namespace=zaaktype_namespace,
                iot_namespace=iot_namespace,
            ):
                zaaktype = ZaakTypeFactory.create()
                iot = InformatieObjectTypeFactory.create(
                    catalogus=zaaktype.catalogus, concept=False
                )
                response = self.client.post(
                    reverse(f"{namespace}:zaaktypeinformatieobjecttype-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "informatieobjecttype": f"http://testserver{reverse(iot, namespace=iot_namespace)}",
                        "volgnummer": 1,
                        "richting": "inkomend",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                expected_iot_namespace = (
                    "catalogi" if namespace == "catalogi" else "documenten"
                )
                self.assertIn(
                    f"{namespace}/api/v1/zaaktype-informatieobjecttypen", data["url"]
                )
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["informatieobjecttype"],
                    f"http://testserver{reverse(iot, namespace=expected_iot_namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakObjectTypeDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = ZaakObjectTypeFactory.create(zaaktype__concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/zaakobjecttypen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("catalogi/api/v1/catalogussen", response.data["catalogus"])

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/zaakobjecttypen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktype"])
        self.assertIn("zaken/api/v1/catalogussen", response.data["catalogus"])

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:zaakobjecttype-list"),
            "/catalogi/api/v1/zaakobjecttypen",
        )
        self.assertEqual(
            reverse("catalogi:zaakobjecttype-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/zaakobjecttypen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:zaakobjecttype-list"),
            "/zaken/api/v1/zaakobjecttypen",
        )
        self.assertEqual(
            reverse("zaken:zaakobjecttype-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/zaakobjecttypen/1",
        )

    def test_create_zaakobjecttype_with_namespaces(self):
        for namespace, zaaktype_namespace in self.NAMESPACE_COMBINATIONS:
            with self.subTest(
                namespace=namespace, zaaktype_namespace=zaaktype_namespace
            ):
                zaaktype = ZaakTypeFactory.create()
                response = self.client.post(
                    reverse(f"{namespace}:zaakobjecttype-list"),
                    {
                        "zaaktype": f"http://testserver{reverse(zaaktype, namespace=zaaktype_namespace)}",
                        "anderObjecttype": False,
                        "objecttype": "http://example.org/objecttypen/1",
                        "relatieOmschrijving": "test description",
                        "beginGeldigheid": "2023-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/zaakobjecttypen", data["url"])
                self.assertEqual(
                    data["zaaktype"],
                    f"http://testserver{reverse(zaaktype, namespace=namespace)}",
                )
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(zaaktype.catalogus, namespace=namespace)}",
                )

    def test_create_zaakobject_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(zaakobjecttype_namespace=namespace):
                zaak = ZaakFactory.create(zaaktype=self.obj.zaaktype)
                response = self.client.post(
                    reverse("zaken:zaakobject-list"),
                    {
                        "zaak": f"http://testserver{reverse(zaak, namespace='zaken')}",
                        "zaakobjecttype": f"http://testserver{reverse(self.obj, namespace=namespace)}",
                        "object": "http://example.org/api/zaakobjecten/8768c581-2817-4fe5-933d-37af92d819dd",
                        "objectType": ZaakobjectTypes.adres,
                        "relatieomschrijving": "test",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertEqual(
                    response.json()["zaakobjecttype"],
                    f"http://testserver{reverse(self.obj, namespace='zaken')}",
                )


class CatalogusDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    # (namespace of the endpoint, namespace of the related urls in the request body)
    NAMESPACE_COMBINATIONS = [
        ("catalogi", "catalogi"),
        ("catalogi", "zaken"),
        ("zaken", "catalogi"),
        ("zaken", "zaken"),
    ]

    def setUp(self):
        super().setUp()
        self.obj = CatalogusFactory.create()
        ZaakTypeFactory.create(catalogus=self.obj, concept=False)
        BesluitTypeFactory.create(catalogus=self.obj, concept=False)
        InformatieObjectTypeFactory.create(catalogus=self.obj, concept=False)

    def test_deprecated_catalogi_api_response(self):
        url = reverse(self.obj, namespace="catalogi")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("catalogi/api/v1/catalogussen", response.data["url"])
        self.assertIn("catalogi/api/v1/zaaktypen", response.data["zaaktypen"][0])
        self.assertIn("catalogi/api/v1/besluittypen", response.data["besluittypen"][0])
        self.assertIn(
            "catalogi/api/v1/informatieobjecttypen",
            response.data["informatieobjecttypen"][0],
        )

    def test_zaken_api_response(self):
        url = reverse(self.obj, namespace="zaken")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zaken/api/v1/catalogussen", response.data["url"])
        self.assertIn("zaken/api/v1/zaaktypen", response.data["zaaktypen"][0])
        self.assertIn("zaken/api/v1/besluittypen", response.data["besluittypen"][0])
        self.assertIn(
            "documenten/api/v1/informatieobjecttypen",
            response.data["informatieobjecttypen"][0],
        )

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("catalogi:catalogus-list"),
            "/catalogi/api/v1/catalogussen",
        )
        self.assertEqual(
            reverse("catalogi:catalogus-detail", kwargs={"uuid": 1}),
            "/catalogi/api/v1/catalogussen/1",
        )

    def test_new_paths(self):
        self.assertEqual(
            reverse("zaken:catalogus-list"),
            "/zaken/api/v1/catalogussen",
        )
        self.assertEqual(
            reverse("zaken:catalogus-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/catalogussen/1",
        )

    def test_create_catalogus_with_namespaces(self):
        for namespace in ("catalogi", "zaken"):
            with self.subTest(namespace=namespace):
                response = self.client.post(
                    reverse(f"{namespace}:catalogus-list"),
                    {
                        "domein": namespace.upper()[:5],
                        "contactpersoonBeheerTelefoonnummer": "0612345679",
                        "rsin": "100000009",
                        "contactpersoonBeheerNaam": "test",
                        "contactpersoonBeheerEmailadres": "test@test.com",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                self.assertIn(
                    f"{namespace}/api/v1/catalogussen", response.json()["url"]
                )

    def test_create_besluittype_with_namespaces(self):
        for i, (namespace, catalogus_namespace) in enumerate(
            self.NAMESPACE_COMBINATIONS
        ):
            with self.subTest(
                namespace=namespace, catalogus_namespace=catalogus_namespace
            ):
                response = self.client.post(
                    reverse(f"{namespace}:besluittype-list"),
                    {
                        "catalogus": f"http://testserver{reverse(self.obj, namespace=catalogus_namespace)}",
                        "omschrijving": f"test {i}",
                        "omschrijvingGeneriek": "",
                        "besluitcategorie": "",
                        "reactietermijn": "P14D",
                        "publicatieIndicatie": True,
                        "publicatietekst": "",
                        "publicatietermijn": None,
                        "toelichting": "",
                        "informatieobjecttypen": [],
                        "beginGeldigheid": "2019-01-01",
                    },
                )
                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.json()
                )
                data = response.json()
                self.assertIn(f"{namespace}/api/v1/besluittypen", data["url"])
                self.assertEqual(
                    data["catalogus"],
                    f"http://testserver{reverse(self.obj, namespace=namespace)}",
                )
