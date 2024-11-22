# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
from django.conf import settings
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.models import CMISConfig, UrlMapping
from rest_framework import status
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ..api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
)
from ..constants import ObjectInformatieObjectTypes
from ..models import ObjectInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory

IOTYPE_EXTERNAL = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"


@require_cmis
@override_settings(CMIS_ENABLED=True)
class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APICMISTestCase):
    def test_cannot_create_io_without_correct_scope(self):
        url = reverse("enkelvoudiginformatieobject-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        oio = ObjectInformatieObject.objects.get()
        urls = [
            reverse("enkelvoudiginformatieobject-list"),
            reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}),
            reverse("gebruiksrechten-list"),
            reverse(gebruiksrechten),
            reverse("objectinformatieobject-list"),
            reverse(oio),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


@require_cmis
@override_settings(CMIS_ENABLED=True)
class InformatieObjectReadCorrectScopeTests(JWTAuthMixin, APICMISTestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        super().setUpTestData()

    def test_io_list(self):
        """
        Assert you can only list INFORMATIEOBJECTen of the informatieobjecttypen and vertrouwelijkheidaanduiding
        of your authorization
        """
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["informatieobjecttype"],
            f"http://testserver{reverse(self.informatieobjecttype)}",
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_io_retrieve(self):
        """
        Assert you can only read INFORMATIEOBJECTen of the informatieobjecttype and vertrouwelijkheidaanduiding
        of your authorization
        """
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url1 = reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio1.uuid})
        url2 = reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio2.uuid})

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    @tag("gh-1661")
    def test_eio_list_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to see EnkelvoudigInformatieObjecten in the list view
        that belong to Informatieobjecttypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.informatieobjecttype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Should be visible
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # Different catalogus, should not be visible
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # Correct catalogus, but VA is too high, should not be visible
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        # Different catalogus, should not be visible
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["informatieobjecttype"],
            f"http://testserver{reverse(self.informatieobjecttype)}",
        )
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    @tag("gh-1661")
    def test_eio_retrieve_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to read EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.informatieobjecttype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        # Not part of catalogus
        eio_incorrect_catalogus = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        # vertrouwelijkheidaanduiding too high
        eio_incorrect_va = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        # allowed to access!
        eio_allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response_not_allowed1 = self.client.get(reverse(eio_incorrect_catalogus))
        response_not_allowed2 = self.client.get(reverse(eio_incorrect_va))
        response_allowed = self.client.get(reverse(eio_allowed))

        self.assertEqual(response_not_allowed1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_not_allowed2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response_allowed.status_code, status.HTTP_200_OK)

    def test_read_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(len(response_data), 4)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class InformatieObjectWriteCorrectScopeTests(JWTAuthMixin, APICMISTestCase):
    scopes = [
        SCOPE_DOCUMENTEN_BIJWERKEN,
        SCOPE_DOCUMENTEN_AANMAKEN,
        SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    ]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        super().setUpTestData()

        cls.informatieobjecttype_not_allowed = InformatieObjectTypeFactory.create(
            concept=False
        )
        cls.applicatie.autorisaties.all().delete()
        CatalogusAutorisatieFactory.create(
            catalogus=cls.informatieobjecttype.catalogus,
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    @tag("gh-1661")
    def test_eio_create_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to create EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        url = reverse("enkelvoudiginformatieobject-list")

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.post(
                url,
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype_not_allowed)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.post(
                url,
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.geheim,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.post(
                url,
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

    @tag("gh-1661")
    def test_eio_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to update EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        eio_allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # To allow updates
        eio_allowed.canonical.lock_document(eio_allowed.uuid)
        eio_incorrect_catalogus = EnkelvoudigInformatieObjectFactory.create()
        eio_incorrect_va = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.put(
                reverse(eio_incorrect_catalogus),
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.put(
                reverse(eio_incorrect_va),
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.put(
                reverse(eio_allowed),
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                    "lock": eio_allowed.canonical.lock,
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_eio_partially_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to partially update EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        eio_allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # To allow updates
        eio_allowed.canonical.lock_document(eio_allowed.uuid)
        eio_incorrect_catalogus = EnkelvoudigInformatieObjectFactory.create()
        eio_incorrect_va = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.patch(
                reverse(eio_incorrect_catalogus), {"titel": "foo"}
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.patch(reverse(eio_incorrect_va), {"titel": "foo"})

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.patch(
                reverse(eio_allowed),
                {"titel": "foo", "lock": eio_allowed.canonical.lock},
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_eio_delete_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to delete EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        eio_allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio_incorrect_catalogus = EnkelvoudigInformatieObjectFactory.create()
        eio_incorrect_va = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.delete(reverse(eio_incorrect_catalogus))

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.delete(reverse(eio_incorrect_va))

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.delete(reverse(eio_allowed))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )


@require_cmis
@override_settings(CMIS_ENABLED=True)
class GebruiksrechtenReadTests(JWTAuthMixin, APICMISTestCase):

    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN, SCOPE_DOCUMENTEN_AANMAKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        super().setUpTestData()

    def test_list_gebruiksrechten_limited_to_authorized_zaken(self):
        url = reverse("gebruiksrechten-list")

        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        gebruiksrechten1 = GebruiksrechtenCMISFactory(informatieobject=eio1_url)

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        GebruiksrechtenCMISFactory(informatieobject=eio2_url)

        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        GebruiksrechtenCMISFactory(informatieobject=eio3_url)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(gebruiksrechten1)}"
        )

    @tag("gh-1661")
    def test_list_gebruiksrechten_limited_to_authorized_zaken_with_catalogus_autorisatie(
        self,
    ):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.informatieobjecttype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("gebruiksrechten-list")
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        gebruiksrechten1 = GebruiksrechtenCMISFactory(informatieobject=eio1_url)

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        GebruiksrechtenCMISFactory(informatieobject=eio2_url)

        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        GebruiksrechtenCMISFactory(informatieobject=eio3_url)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(gebruiksrechten1)}"
        )

    def test_create_gebruiksrechten_limited_to_authorized_io(self):
        url = reverse("gebruiksrechten-list")
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        for eio in [eio1, eio2]:
            with self.subTest(
                informatieobjecttype=eio.informatieobjecttype,
                vertrouwelijkheidaanduiding=eio.vertrouwelijkheidaanduiding,
            ):
                response = self.client.post(
                    url,
                    {
                        "informatieobject": reverse(
                            "enkelvoudiginformatieobject-detail",
                            kwargs={"uuid": eio.uuid},
                        ),
                        "startdatum": "2018-12-24T00:00:00Z",
                        "omschrijvingVoorwaarden": "Een hele set onredelijke voorwaarden",
                    },
                )

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_gebruiksrechten_limited_to_authorized_io_cmis(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        gebruiksrechten1 = GebruiksrechtenCMISFactory(informatieobject=eio1_url)

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        gebruiksrechten2 = GebruiksrechtenCMISFactory(informatieobject=eio2_url)

        response1 = self.client.get(reverse(gebruiksrechten1))
        response2 = self.client.get(reverse(gebruiksrechten2))

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)


@require_cmis
@override_settings(CMIS_ENABLED=True)
class OioReadTests(JWTAuthMixin, APICMISTestCase):

    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        if settings.CMIS_URL_MAPPING_ENABLED:
            config = CMISConfig.get_solo()

            UrlMapping.objects.create(
                long_pattern="https://externe.catalogus.nl",
                short_pattern="https://xcat.nl",
                config=config,
            )

        super().setUpTestData()

    def test_detail_oio_limited_to_authorized_zaken_cmis(self):
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        oio3 = ObjectInformatieObject.objects.create(
            informatieobject=eio3_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        with self.subTest(
            informatieobjecttype=eio1.informatieobjecttype,
            vertrouwelijkheidaanduiding=eio1.vertrouwelijkheidaanduiding,
        ):
            url = reverse(oio1)

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for oio, eio in ((oio2, eio2), (oio3, eio3)):
            with self.subTest(
                informatieobjecttype=eio.informatieobjecttype,
                vertrouwelijkheidaanduiding=eio.vertrouwelijkheidaanduiding,
            ):
                url = reverse(oio)

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @tag("gh-1661")
    def test_list_oio_limited_to_authorized_zaken_with_catalogus_autorisatie(self):
        self.applicatie.autorisaties.all().delete()

        CatalogusAutorisatieFactory.create(
            catalogus=self.informatieobjecttype.catalogus,
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        url = reverse("objectinformatieobject-list")
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio3_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_list_oio_limited_to_authorized_zaken_cmis(self):
        url = reverse("objectinformatieobject-list")

        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio3_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")


@tag("external-urls")
@require_cmis
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class InternalInformatietypeScopeTests(JWTAuthMixin, APICMISTestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        if settings.CMIS_URL_MAPPING_ENABLED:
            config = CMISConfig.get_solo()

            UrlMapping.objects.create(
                long_pattern="https://externe.catalogus.nl",
                short_pattern="https://xcat.nl",
                config=config,
            )

        super().setUpTestData()

    def test_eio_list(self):
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["informatieobjecttype"],
            f"http://testserver{reverse(self.informatieobjecttype)}",
        )

    def test_eio_retreive(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(eio1)
        url2 = reverse(eio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_oio_list(self):
        url = reverse("objectinformatieobject-list")

        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"

        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_oio_retrieve(self):
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"

        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls")
@require_cmis
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalInformatieObjectInformatieObjectTypescopeTests(
    JWTAuthMixin, APICMISTestCase
):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    informatieobjecttype = IOTYPE_EXTERNAL
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        if settings.CMIS_URL_MAPPING_ENABLED:
            config = CMISConfig.get_solo()

            UrlMapping.objects.create(
                long_pattern="https://externe.catalogus.nl",
                short_pattern="https://xcat.nl",
                config=config,
            )

    def test_eio_list(self):
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["informatieobjecttype"], IOTYPE_EXTERNAL)

    def test_eio_retreive(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(eio1)
        url2 = reverse(eio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_oio_list(self):
        url = reverse("objectinformatieobject-list")
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_oio_retrieve(self):
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )
        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
