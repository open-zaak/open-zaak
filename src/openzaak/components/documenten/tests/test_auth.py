# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization amchinery is in place.
"""

from django.test import override_settings, tag

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import (
    AuthCheckMixin,
    get_validation_errors,
    reverse,
    reverse_lazy,
)

from openzaak.components.autorisaties.tests.factories import CatalogusAutorisatieFactory
from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_ALLES_LEZEN
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.components.zaken.tests.utils import ZAAK_READ_KWARGS
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_LOCK,
)
from ..constants import ObjectInformatieObjectTypes
from ..models import ObjectInformatieObject, ReservedDocument
from .factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
    VerzendingFactory,
)
from .utils import get_operation_url

IOTYPE_EXTERNAL = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"
IOTYPE_EXTERNAL2 = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/a7634cc6-b312-4d75-ba4d-a12e1fdb1dee"


class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_io_without_correct_scope(self):
        urls = [
            reverse("enkelvoudiginformatieobject-list"),
            reverse("enkelvoudiginformatieobject--zoek"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertForbidden(url, method="post")

    def test_cannot_create_verzending_without_correct_scope(self):
        url = reverse("verzending-list")
        eio = EnkelvoudigInformatieObjectFactory()
        self.assertForbidden(
            url,
            method="post",
            request_kwargs={
                "data": {
                    "informatieobject": reverse(
                        "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
                    )
                }
            },
        )

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


@temp_private_root()
@override_settings(OPENZAAK_DOMAIN="testserver")
class InformatieObjectReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
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

    @tag("gh-security-issues-5")
    def test_io_zoek(self):
        """
        Regression test for open-zaak/security-issues#5

        Assert you can only search from INFORMATIEOBJECTen of the informatieobjecttypen
        and vertrouwelijkheidaanduiding of your authorization
        """

        eio_authorized = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio_unauthorized_other_iotype = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio_unauthorized_too_high_confidentiality = (
            EnkelvoudigInformatieObjectFactory.create(
                informatieobjecttype=self.informatieobjecttype,
                vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            )
        )
        eio_unauthorized_other_iotype_and_too_high_confidentiality = (
            EnkelvoudigInformatieObjectFactory.create(
                vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim
            )
        )
        url = get_operation_url("enkelvoudiginformatieobject__zoek")

        response = self.client.post(
            url,
            {
                "uuid__in": [
                    eio_authorized.uuid,
                    eio_unauthorized_other_iotype.uuid,
                    eio_unauthorized_too_high_confidentiality.uuid,
                    eio_unauthorized_other_iotype_and_too_high_confidentiality.uuid,
                ]
            },
        )

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


@override_settings(OPENZAAK_DOMAIN="testserver")
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

        with self.subTest("without vertrouwelijkheidaanduiding"):
            response = self.client.post(
                url,
                {
                    "informatieobjecttype": f"http://testserver{reverse(self.informatieobjecttype)}",
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

        with self.subTest("without informatieobjecttype"):
            response = self.client.post(
                url,
                {
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "creatiedatum": "2018-12-24",
                    "titel": "foo",
                    "auteur": "bar",
                    "taal": "nld",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, response.data
            )
            error = get_validation_errors(response, "informatieobjecttype")
            self.assertEqual(error["code"], "required")

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


@override_settings(OPENZAAK_DOMAIN="testserver")
class GebruiksrechtenReadTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN, SCOPE_DOCUMENTEN_AANMAKEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
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
@override_settings(ALLOWED_HOSTS=["testserver"], OPENZAAK_DOMAIN="testserver")
class InternalInformatietypeScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
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
@override_settings(
    ALLOWED_HOSTS=["testserver"], DEBUG=True, OPENZAAK_DOMAIN="testserver"
)
class ExternalInformatieObjectInformatieObjectTypescopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    informatieobjecttype = IOTYPE_EXTERNAL
    component = ComponentTypes.drc

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


@override_settings(OPENZAAK_DOMAIN="testserver")
class VerzendingReadCorrectScopeTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
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


@tag("gh-2018")
class ReserveDocumentAuthTests(JWTAuthMixin, APITestCase):
    url = reverse_lazy("reserveddocument-list")
    bronorganisatie = "812345678"

    def setUp(self):
        super().setUp()

    def test_post_reserve_document_forbidden_without_scope(self):
        # Don't assign any scopes
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component="drc",
            scopes=[],
        )

        response = self.client.post(self.url, {"bronorganisatie": self.bronorganisatie})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_reserve_document_allowed_with_scope(self):
        # Assign the correct scope
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component="drc",
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN],
        )

        response = self.client.post(self.url, {"bronorganisatie": self.bronorganisatie})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.data
        self.assertIn("identificatie", response_data)
        self.assertTrue(
            ReservedDocument.objects.filter(
                identificatie=response_data["identificatie"],
                bronorganisatie=self.bronorganisatie,
            ).exists()
        )


@tag("gh-2452")
@temp_private_root()
@override_settings(OPENZAAK_DOMAIN="testserver")
class AlleenIsGereedVoorPublicatieTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = False
    alleen_is_gereed_voor_publicatie = True

    component = ComponentTypes.drc
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN, SCOPE_DOCUMENTEN_LOCK]
    maxDiff = None

    def setUp(self):
        super().setUp()

        informatieobjecttype = InformatieObjectTypeFactory()
        self.autorisatie.informatieobjecttype = (
            f"http://testserver{reverse(informatieobjecttype)}"
        )
        self.autorisatie.save(update_fields=["informatieobjecttype"])

        # Create three documents, two that are is_gereed_voor_publicatie=True and one that is not.
        self.is_gereed_voor_publicatie_data = EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=informatieobjecttype,
            is_gereed_voor_publicatie=True,
        )
        EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=informatieobjecttype,
            is_gereed_voor_publicatie=True,
        )
        self.niet_gereed_voor_publicatie_data = EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=informatieobjecttype,
            is_gereed_voor_publicatie=False,
        )

    def test_list_and_get_includes_all_documents_if_alleen_is_gereed_voor_publicatie_false(
        self,
    ):
        # This test should all get all the EIO documents
        self.applicatie.alleen_is_gereed_voor_publicatie = False
        self.applicatie.save(update_fields=["alleen_is_gereed_voor_publicatie"])

        # Get list
        response = self.client.get(reverse("enkelvoudiginformatieobject-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

        # Get detail
        response = self.client.get(reverse(self.is_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(reverse(self.niet_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_excludes_niet_gereed_voor_publicatie_documents(self):
        response = self.client.get(reverse("enkelvoudiginformatieobject-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(self.is_gereed_voor_publicatie_data)}",
        )

    def test_search_excludes_niet_gereed_voor_publicatie_documents(self):
        response = self.client.post(
            reverse("enkelvoudiginformatieobject--zoek"),
            {
                "uuid__in": [
                    str(self.is_gereed_voor_publicatie_data.uuid),
                    str(self.niet_gereed_voor_publicatie_data.uuid),
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(self.is_gereed_voor_publicatie_data)}",
        )

    def test_detail_excludes_niet_gereed_voor_publicatie_documents(self):
        response = self.client.get(reverse(self.niet_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_includes_is_gereed_voor_publicatie_documents(self):
        response = self.client.get(reverse(self.is_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_excludes_niet_gereed_voor_publicatie_documents(self):
        response = self.client.get(
            reverse(
                "enkelvoudiginformatieobject-download",
                kwargs={"uuid": self.niet_gereed_voor_publicatie_data.uuid},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_includes_is_gereed_voor_publicatie_documents(self):
        response = self.client.get(
            reverse(
                "enkelvoudiginformatieobject-download",
                kwargs={"uuid": self.is_gereed_voor_publicatie_data.uuid},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_lock_excludes_niet_gereed_voor_publicatie_documents(self):
        response = self.client.post(
            reverse(
                "enkelvoudiginformatieobject-lock",
                kwargs={"uuid": self.niet_gereed_voor_publicatie_data.uuid},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lock_includes_is_gereed_voor_publicatie_documents(self):
        response = self.client.post(
            reverse(
                "enkelvoudiginformatieobject-lock",
                kwargs={"uuid": self.is_gereed_voor_publicatie_data.uuid},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_all_authorizations_still_restrict_is_gereed_voor_publicatie(self):
        self.applicatie.autorisaties.all().delete()
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save(update_fields=["heeft_alle_autorisaties"])

        response = self.client.get(reverse("enkelvoudiginformatieobject-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(self.is_gereed_voor_publicatie_data)}",
        )

        # Test that the detail view still restricts access to documents that are not is_gereed_voor_publicatie.
        response = self.client.get(reverse(self.niet_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_related_resource_uses_latest_io_with_is_gereed_voor_publicatie(self):
        """
        Test that if a document has multiple versions,
        the related resource will use the latest version that is is_gereed_voor_publicatie=True
        """
        resource = GebruiksrechtenFactory(
            informatieobject=self.niet_gereed_voor_publicatie_data.canonical
        )
        response = self.client.get(reverse(resource))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=self.niet_gereed_voor_publicatie_data.informatieobjecttype,
            canonical=self.niet_gereed_voor_publicatie_data.canonical,
            uuid=self.niet_gereed_voor_publicatie_data.uuid,
            versie=2,
            is_gereed_voor_publicatie=True,
        )
        response = self.client.get(reverse(resource))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_related_lists_exclude_documents_niet_gereed_voor_publicatie(self):
        for factory, endpoint, paginated in (
            (GebruiksrechtenFactory, "gebruiksrechten-list", False),
            (VerzendingFactory, "verzending-list", True),
        ):
            with self.subTest(endpoint=endpoint):
                included = factory(
                    informatieobject=self.is_gereed_voor_publicatie_data.canonical
                )
                factory(
                    informatieobject=self.niet_gereed_voor_publicatie_data.canonical
                )

                response = self.client.get(reverse(endpoint))

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                results = response.data["results"] if paginated else response.data
                self.assertEqual(
                    [item["url"] for item in results],
                    [f"http://testserver{reverse(included)}"],
                )

    def test_eio_old_version_with_niet_gereed_voor_publicatie_access_denied(self):
        """
        Test that an old version of an informatieobject with is_gereed_voor_publicatie=False is denied access.
        Then access it with a new version that is is_gereed_voor_publicatie=True and check that access is granted.
        """
        EnkelvoudigInformatieObjectFactory(
            informatieobjecttype=self.niet_gereed_voor_publicatie_data.informatieobjecttype,
            canonical=self.niet_gereed_voor_publicatie_data.canonical,
            uuid=self.niet_gereed_voor_publicatie_data.uuid,
            versie=2,
            is_gereed_voor_publicatie=True,
        )
        response = self.client.get(
            reverse(self.niet_gereed_voor_publicatie_data), {"versie": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(reverse(self.niet_gereed_voor_publicatie_data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_niet_gereed_voor_publicatie_document_follows_configured_scopes(
        self,
    ):
        url = reverse(self.niet_gereed_voor_publicatie_data)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.autorisatie.scopes.append(SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN)
        self.autorisatie.save(update_fields=["scopes"])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_zaak_list_filters_document_links_and_expansions(self):
        """
        Checks that the zaak list endpoint filters the zaakinformatieobjecten
        based on the is_gereed_voor_publicatie status of the linked documents,
        and that the expand parameter works correctly.
        """
        zaak = ZaakFactory()
        other_zaak = ZaakFactory(zaaktype=zaak.zaaktype)

        # Add zaak auth
        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            zaaktype=f"http://testserver{reverse(zaak.zaaktype)}",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        included = ZaakInformatieObjectFactory(
            zaak=zaak, informatieobject=self.is_gereed_voor_publicatie_data.canonical
        )
        excluded = ZaakInformatieObjectFactory(
            zaak=zaak, informatieobject=self.niet_gereed_voor_publicatie_data.canonical
        )

        for is_gereed_voor_publicatie in (True, False):
            # Set the applicatie allen_is_gereed_voor_publicatie auth
            self.applicatie.alleen_is_gereed_voor_publicatie = is_gereed_voor_publicatie
            self.applicatie.save(update_fields=["alleen_is_gereed_voor_publicatie"])

            # Prepare the expected results
            expected = [included] if is_gereed_voor_publicatie else [included, excluded]
            expected_urls = [
                f"http://testserver{reverse(relation)}" for relation in expected
            ]

            with self.subTest(
                is_gereed_voor_publicatie=is_gereed_voor_publicatie,
            ):
                response = self.client.get(
                    reverse("zaak-list"),
                    {
                        "expand": "zaakinformatieobjecten,zaakinformatieobjecten.informatieobject"
                    },
                    **ZAAK_READ_KWARGS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # Check that the results only include the expected zaak URLs.
                results = {item["url"]: item for item in response.json()["results"]}
                self.assertCountEqual(
                    results,
                    [
                        f"http://testserver{reverse(item)}"
                        for item in (zaak, other_zaak)
                    ],
                )

                data = results[f"http://testserver{reverse(zaak)}"]
                # Check the zaakinformatieobjected URLs in the main data
                self.assertCountEqual(data["zaakinformatieobjecten"], expected_urls)

                # Check the zaakinformatieobjected URLs in the expanded data
                self.assertCountEqual(
                    [item["url"] for item in data["_expand"]["zaakinformatieobjecten"]],
                    expected_urls,
                )

    def test_zaakinformatieobject_list_omits_niet_gereed_voor_publicatie_documents(
        self,
    ):
        # Prepare 3 documents that are ready for publication and 2 that are not, all linked to the same zaak.
        zio_gereed_voor_publicatie = ZaakInformatieObjectFactory.create_batch(
            3, informatieobject=self.is_gereed_voor_publicatie_data.canonical
        )
        zio_niet_gereed_voor_publicatie = ZaakInformatieObjectFactory.create_batch(
            2, informatieobject=self.niet_gereed_voor_publicatie_data.canonical
        )

        # Add zaak auth
        for i in range(len(zio_gereed_voor_publicatie)):
            Autorisatie.objects.create(
                applicatie=self.applicatie,
                component=ComponentTypes.zrc,
                scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
                zaaktype=f"http://testserver{reverse(zio_gereed_voor_publicatie[i].zaak.zaaktype)}",
                max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            )

        for i in range(len(zio_niet_gereed_voor_publicatie)):
            Autorisatie.objects.create(
                applicatie=self.applicatie,
                component=ComponentTypes.zrc,
                scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
                zaaktype=f"http://testserver{reverse(zio_niet_gereed_voor_publicatie[i].zaak.zaaktype)}",
                max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            )

        response = self.client.get(
            reverse("zaakinformatieobject-list"), {"expand": "informatieobject"}
        )

        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            sorted([item["uuid"] for item in data]),
            sorted([str(item.uuid) for item in zio_gereed_voor_publicatie]),
        )
