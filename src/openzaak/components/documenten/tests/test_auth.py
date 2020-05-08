"""
Guarantee that the proper authorization amchinery is in place.
"""
from unittest import skipIf

import requests_mock
from django.conf import settings
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    ComponentTypes,
    ObjectTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.utils.tests import APITestCaseCMIS, JWTAuthMixin

from ..api.scopes import SCOPE_DOCUMENTEN_AANMAKEN, SCOPE_DOCUMENTEN_ALLES_LEZEN
from ..models import ObjectInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory, GebruiksrechtenFactory
from .utils import get_eio_response

IOTYPE_EXTERNAL = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"


class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APITestCaseCMIS):
    def test_cannot_create_io_without_correct_scope(self):
        url = reverse("enkelvoudiginformatieobject-list")
        self.assertForbidden(url, method="post")

    @override_settings(CMIS_ENABLED=False)
    def test_cannot_read_without_correct_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        if settings.CMIS_ENABLED:
            gebruiksrechten = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)
        else:
            gebruiksrechten = GebruiksrechtenFactory.create()
        ZaakInformatieObjectFactory.create()
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

    @override_settings(CMIS_ENABLED=True)
    def test_cannot_read_without_correct_scope_cmis(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri("GET", eio_url, json=get_eio_response(reverse(eio)))
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


class InformatieObjectReadCorrectScopeTests(JWTAuthMixin, APITestCaseCMIS):
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


class GebruiksrechtenReadTests(JWTAuthMixin, APITestCaseCMIS):

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

    @override_settings(CMIS_ENABLED=True)
    def test_list_gebruiksrechten_limited_to_authorized_zaken_cmis(self):
        url = reverse("gebruiksrechten-list")

        eio1 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        gebruiksrechten1 = GebruiksrechtenCMISFactory(
            informatieobject=eio1_url
        )

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        GebruiksrechtenCMISFactory(
            informatieobject=eio2_url
        )

        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        GebruiksrechtenCMISFactory(
            informatieobject=eio3_url
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(
            response_data[0]["url"], f"http://testserver{reverse(gebruiksrechten1)}"
        )

    @override_settings(CMIS_ENABLED=False)
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

    @override_settings(CMIS_ENABLED=False)
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

    @override_settings(CMIS_ENABLED=True)
    def test_read_gebruiksrechten_limited_to_authorized_io_cmis(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio1_url = f"http://testserver{reverse(eio1)}"
        gebruiksrechten1 = GebruiksrechtenCMISFactory(
            informatieobject=eio1_url
        )

        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        gebruiksrechten2 = GebruiksrechtenCMISFactory(
            informatieobject=eio2_url
        )

        response1 = self.client.get(reverse(gebruiksrechten1))
        response2 = self.client.get(reverse(gebruiksrechten2))

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)


@override_settings(CMIS_ENABLED=False)
class OioReadTests(JWTAuthMixin, APITestCaseCMIS):

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
            informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        ObjectInformatieObject.objects.create(
            informatieobject=eio3.canonical, zaak=zaak, object_type=ObjectTypes.zaak
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
            informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        oio3 = ObjectInformatieObject.objects.create(
            informatieobject=eio3.canonical, zaak=zaak, object_type=ObjectTypes.zaak
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


@override_settings(CMIS_ENABLED=True)
class OioReadCMISTests(JWTAuthMixin, APITestCaseCMIS):

    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
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
            informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        oio3 = ObjectInformatieObject.objects.create(
            informatieobject=eio3_url, zaak=zaak, object_type=ObjectTypes.zaak
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
            informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        # must not show up
        eio3 = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        eio3_url = f"http://testserver{reverse(eio3)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio3_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class InternalInformatietypeScopeTests(JWTAuthMixin, APITestCaseCMIS):
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

        if settings.CMIS_ENABLED:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        if settings.CMIS_ENABLED:
            ObjectInformatieObject.objects.create(
                informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            ObjectInformatieObject.objects.create(
                informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
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

        if settings.CMIS_ENABLED:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        if settings.CMIS_ENABLED:
            oio2 = ObjectInformatieObject.objects.create(
                informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio2 = ObjectInformatieObject.objects.create(
                informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )

        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ExternalInformatieobjecttypeScopeTests(JWTAuthMixin, APITestCaseCMIS):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    informatieobjecttype = IOTYPE_EXTERNAL
    component = ComponentTypes.drc

    def setUp(self):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        return super().setUp()

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
        if settings.CMIS_ENABLED:
            eio1_url = f"http://testserver{reverse(eio1)}"
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        if settings.CMIS_ENABLED:
            eio2_url = f"http://testserver{reverse(eio2)}"
            ObjectInformatieObject.objects.create(
                informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            ObjectInformatieObject.objects.create(
                informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
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
        if settings.CMIS_ENABLED:
            eio1_url = f"http://testserver{reverse(eio1)}"
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio1 = ObjectInformatieObject.objects.create(
                informatieobject=eio1.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )

        # must not show up
        eio2 = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        if settings.CMIS_ENABLED:
            eio2_url = f"http://testserver{reverse(eio2)}"
            oio2 = ObjectInformatieObject.objects.create(
                informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
            )
        else:
            oio2 = ObjectInformatieObject.objects.create(
                informatieobject=eio2.canonical, zaak=zaak, object_type=ObjectTypes.zaak
            )
        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
