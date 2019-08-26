"""
Guarantee that the proper authorization amchinery is in place.
"""
from unittest import skip

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.catalogi.models.tests.factories import (
    InformatieObjectTypeFactory,
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
    ObjectInformatieObjectFactory,
)
from openzaak.utils.tests import JWTAuthMixin

from ..scopes import SCOPE_DOCUMENTEN_AANMAKEN, SCOPE_DOCUMENTEN_ALLES_LEZEN


class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APITestCase):
    def test_cannot_create_io_without_correct_scope(self):
        url = reverse("enkelvoudiginformatieobject-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        gebruiksrechten = GebruiksrechtenFactory.create()
        # oio = ObjectInformatieObjectFactory.create(is_besluit=True)
        urls = [
            reverse("enkelvoudiginformatieobject-list"),
            reverse("enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}),
            reverse("gebruiksrechten-list"),
            reverse(gebruiksrechten),
            # FIXME add when objectinformatieobject is implemented
            # reverse('objectinformatieobject-list'),
            # reverse('objectinformatieobject-'),
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
        super().setUpTestData()

    def test_io_list(self):
        """
        Assert you can only list INFORMATIEOBJECTen of the informatieobjecttypes and vertrouwelijkheidaanduiding
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


@skip("ObjectInformatieObject is not implemented yet")
class OioReadTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    informatieobjecttype = "https://informatieobjecttype.nl/ok"
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar

    def test_list_oio_limited_to_authorized_zaken(self):
        url = reverse("objectinformatieobject-list")
        # must show up
        oio1 = ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            is_zaak=True,
        )
        # must not show up
        ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            is_zaak=True,
        )
        # must not show up
        ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/not_ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            is_zaak=True,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_detail_oio_limited_to_authorized_zaken(self):
        # must show up
        oio1 = ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            is_zaak=True,
        )
        # must not show up
        oio2 = ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            is_zaak=True,
        )
        # must not show up
        oio3 = ObjectInformatieObjectFactory.create(
            informatieobject__latest_version__informatieobjecttype="https://informatieobjecttype.nl/not_ok",
            informatieobject__latest_version__vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            is_zaak=True,
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
