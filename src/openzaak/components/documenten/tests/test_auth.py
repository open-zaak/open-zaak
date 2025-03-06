# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization amchinery is in place.
"""
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
)
from ..constants import ObjectInformatieObjectTypes
from ..models import ObjectInformatieObject
from .factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
    VerzendingFactory,
)

IOTYPE_EXTERNAL = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"
IOTYPE_EXTERNAL2 = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/a7634cc6-b312-4d75-ba4d-a12e1fdb1dee"


class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_io_without_correct_scope(self):
        urls = [
            reverse("enkelvoudiginformatieobject-list"),
            reverse("enkelvoudiginformatieobject--zoek"),
            reverse("verzending-list"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        gebruiksrechten = GebruiksrechtenFactory.create()
        ZaakInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.get()
        verzending = VerzendingFactory.create()
        urls = [
            reverse("enkelvoudiginformatieobject-list"),
            reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}),
            reverse("gebruiksrechten-list"),
            reverse(gebruiksrechten),
            reverse("objectinformatieobject-list"),
            reverse(oio),
            reverse("verzending-list"),
            reverse(verzending),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="get")


class InformatieObjectReadCorrectScopeTests(JWTAuthMixin, APITestCase):
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


class InformatieObjectWriteCorrectScopeTests(JWTAuthMixin, APITestCase):
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

        # Different catalogus, should not be allowed
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
        cls.eio_allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=cls.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        cls.eio_incorrect_catalogus = EnkelvoudigInformatieObjectFactory.create()
        cls.eio_incorrect_va = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=cls.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
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
        # To allow updates
        self.eio_allowed.canonical.lock = "foo"
        self.eio_allowed.canonical.save()

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.put(
                reverse(self.eio_incorrect_catalogus),
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
                reverse(self.eio_incorrect_va),
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
                reverse(self.eio_allowed),
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                    "lock": "foo",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_eio_partially_update_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to partially update EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        # To allow updates
        self.eio_allowed.canonical.lock = "foo"
        self.eio_allowed.canonical.save()

        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.patch(
                reverse(self.eio_incorrect_catalogus), {"titel": "foo"}
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.patch(
                reverse(self.eio_incorrect_va), {"titel": "foo"}
            )

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.patch(
                reverse(self.eio_allowed), {"titel": "foo", "lock": "foo"}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @tag("gh-1661")
    def test_eio_delete_with_catalogus_autorisatie(self):
        """
        Assert that CatalogusAutorisatie gives permission to delete EnkelvoudigInformatieObjecten
        that belong to Informatieobjecttypen in the Catalogus
        """
        with self.subTest("correct VA but incorrect catalogus"):
            response = self.client.delete(reverse(self.eio_incorrect_catalogus))

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("correct catalogus but incorrect VA"):
            response = self.client.delete(reverse(self.eio_incorrect_va))

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

        with self.subTest("success"):
            response = self.client.delete(reverse(self.eio_allowed))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )


class GebruiksrechtenReadTests(JWTAuthMixin, APITestCase):

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
        # must show up
        gebruiksrechten1 = GebruiksrechtenFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        GebruiksrechtenFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        GebruiksrechtenFactory.create(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

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
        # must show up
        gebruiksrechten1 = GebruiksrechtenFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        GebruiksrechtenFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        GebruiksrechtenFactory.create(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

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

    def test_read_gebruiksrechten_limited_to_authorized_io(self):
        gebruiksrechten1 = GebruiksrechtenFactory(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        gebruiksrechten2 = GebruiksrechtenFactory(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response1 = self.client.get(reverse(gebruiksrechten1))
        response2 = self.client.get(reverse(gebruiksrechten2))

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)


class OioReadTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        super().setUpTestData()

    def test_list_oio_limited_to_authorized_zaken(self):
        url = reverse("objectinformatieobject-list")
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio3.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

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
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio3.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_detail_oio_limited_to_authorized_zaken(self):
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        oio3 = ObjectInformatieObject.objects.create(
            informatieobject=eio3.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        with self.subTest(
            informatieobjecttype=oio1.informatieobject.latest_version.informatieobjecttype,
            vertrouwelijkheidaanduiding=oio1.informatieobject.latest_version.vertrouwelijkheidaanduiding,
        ):
            url = reverse(oio1)

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # not allowed to see these
        for oio in (oio2, oio3):
            with self.subTest(
                informatieobjecttype=oio.informatieobject.latest_version.informatieobjecttype,
                vertrouwelijkheidaanduiding=oio.informatieobject.latest_version.vertrouwelijkheidaanduiding,
            ):
                url = reverse(oio)

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class InternalInformatietypeScopeTests(JWTAuthMixin, APITestCase):
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

    def test_eio_list_internal_and_external_with_filtering(self):
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes or [],
            zaaktype="",
            informatieobjecttype=IOTYPE_EXTERNAL,
            besluittype="",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            bronorganisatie="000000000",
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            bronorganisatie="000000000",
        )

        # Should not show up due to filtering
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            bronorganisatie="123456789",
        )
        # Should not show up due to lacking permissions
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
            bronorganisatie="000000000",
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            bronorganisatie="000000000",
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url, {"bronorganisatie": "000000000"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0]["informatieobjecttype"],
            f"http://testserver{reverse(self.informatieobjecttype)}",
        )
        self.assertEqual(
            results[1]["informatieobjecttype"],
            IOTYPE_EXTERNAL,
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

        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
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
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@temp_private_root()
@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"], DEBUG=True)
class ExternalInformatieObjectInformatieObjectTypescopeTests(JWTAuthMixin, APITestCase):
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

    def test_eio_list(self):
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            inhoud__filename="file1.bin",
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            inhoud__filename="file2.bin",
        )
        url = reverse("enkelvoudiginformatieobject-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["informatieobjecttype"], IOTYPE_EXTERNAL)

    def test_eio_retreive(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            inhoud__filename="file3.bin",
        )
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            inhoud__filename="file4.bin",
        )
        url1 = reverse(eio1)
        url2 = reverse(eio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK, response1.content)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_oio_list(self):
        url = reverse("objectinformatieobject-list")
        zaak = ZaakFactory.create()
        # must show up
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
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
        oio1 = ObjectInformatieObject.objects.create(
            informatieobject=eio1.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical,
            zaak=zaak,
            object_type=ObjectInformatieObjectTypes.zaak,
        )
        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


class VerzendingReadCorrectScopeTests(JWTAuthMixin, APITestCase):
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

    def test_list_verzendingen_limited_to_authorized_io(self):
        url = reverse("verzending-list")
        # must show up
        verzending = VerzendingFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        # must not show up
        VerzendingFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        # must not show up
        VerzendingFactory.create(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 1)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver{reverse(verzending)}",
        )

    def test_read_verzending_limited_to_authorized_io(self):
        verzending1 = VerzendingFactory(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        verzending2 = VerzendingFactory(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response1 = self.client.get(reverse(verzending1))
        response2 = self.client.get(reverse(verzending2))

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_list_superuser(self):
        """
        superuser read everything
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        VerzendingFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        VerzendingFactory.create(
            informatieobject__latest_version__informatieobjecttype=self.informatieobjecttype,
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        VerzendingFactory.create(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        VerzendingFactory.create(
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse("verzending-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 4)
