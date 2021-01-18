# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Guarantee that the proper authorization machinery is in place.
"""
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import (
    ComponentTypes,
    ObjectTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import AuthCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.utils.tests import (
    APICMISTestCase,
    JWTAuthMixin,
    OioMixin,
    get_eio_response,
)

from ..api.scopes import SCOPE_DOCUMENTEN_AANMAKEN, SCOPE_DOCUMENTEN_ALLES_LEZEN
from ..models import ObjectInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory

IOTYPE_EXTERNAL = "https://externe.catalogus.nl/api/v1/informatieobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class InformatieObjectScopeForbiddenTests(AuthCheckMixin, APICMISTestCase, OioMixin):
    def test_cannot_create_io_without_correct_scope(self):
        url = reverse("enkelvoudiginformatieobject-list")
        self.assertForbidden(url, method="post")

    def test_cannot_read_without_correct_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory.create(informatieobject=eio_url)

        self.adapter.get(eio_url, json=get_eio_response(reverse(eio)))
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        ZaakInformatieObjectFactory.create(informatieobject=eio_url, zaak=zaak)
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


@tag("cmis")
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


@tag("cmis")
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


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class OioReadTests(JWTAuthMixin, APICMISTestCase, OioMixin):

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

    def test_detail_oio_limited_to_authorized_zaken_cmis(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class InternalInformatietypeScopeTests(JWTAuthMixin, APICMISTestCase, OioMixin):
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
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_oio_retrieve(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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
            informatieobjecttype=IOTYPE_EXTERNAL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class ExternalInformatieobjecttypeScopeTests(JWTAuthMixin, APICMISTestCase, OioMixin):
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
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        eio2_url = f"http://testserver{reverse(eio2)}"
        ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], f"http://testserver{reverse(oio1)}")

    def test_oio_retrieve(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
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
            informatieobjecttype="https://externe.catalogus.nl/api/v1/informatieobjecttypen/1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eio2_url = f"http://testserver{reverse(eio2)}"
        oio2 = ObjectInformatieObject.objects.create(
            informatieobject=eio2_url, zaak=zaak, object_type=ObjectTypes.zaak
        )
        url1 = reverse(oio1)
        url2 = reverse(oio2)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
