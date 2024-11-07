# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.catalogi.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..models import (
    EnkelvoudigInformatieObject,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
)


class EnkelvoudigInformatieObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_createdatum(self):
        EnkelvoudigInformatieObjectFactory(creatiedatum="2000-01-01")
        EnkelvoudigInformatieObjectFactory(creatiedatum="2010-01-01")
        EnkelvoudigInformatieObjectFactory(creatiedatum="2020-01-01")

        with self.subTest("gte"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"creatiedatum__gte": "2010-01-01"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["creatiedatum"], "2010-01-01")
            self.assertEqual(data["results"][1]["creatiedatum"], "2020-01-01")

        with self.subTest("lte"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"creatiedatum__lte": "2010-01-01"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["creatiedatum"], "2000-01-01")
            self.assertEqual(data["results"][1]["creatiedatum"], "2010-01-01")

    def test_auteur(self):
        EnkelvoudigInformatieObjectFactory.create(auteur="Alex")
        EnkelvoudigInformatieObjectFactory.create(auteur="Bernard")
        EnkelvoudigInformatieObjectFactory.create(auteur="Bert")

        with self.subTest("exact"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"auteur": "Bernard"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["auteur"], "Bernard")

        with self.subTest("contains"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"auteur": "Ber"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["auteur"], "Bernard")
            self.assertEqual(data["results"][1]["auteur"], "Bert")

    def test_beschrijving(self):
        EnkelvoudigInformatieObjectFactory.create(
            beschrijving="Random Item that won't be retrieved"
        )
        EnkelvoudigInformatieObjectFactory.create(beschrijving="Lorem Ipsum")
        EnkelvoudigInformatieObjectFactory.create(
            beschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        )

        with self.subTest("exact"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {
                    "beschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                },
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(
                data["results"][0]["beschrijving"],
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )

        with self.subTest("contains"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"beschrijving": "Lorem ipsum"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["beschrijving"], "Lorem Ipsum")
            self.assertEqual(
                data["results"][1]["beschrijving"],
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )

    def test_titel(self):
        EnkelvoudigInformatieObjectFactory.create(titel="A...")
        EnkelvoudigInformatieObjectFactory.create(titel="Lorem")
        EnkelvoudigInformatieObjectFactory.create(titel="Lorem Ipsum")

        with self.subTest("exact"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"titel": "Lorem Ipsum"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "Lorem Ipsum")

        with self.subTest("contains"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"titel": "Lorem"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["titel"], "Lorem")
            self.assertEqual(data["results"][1]["titel"], "Lorem Ipsum")

    def test_vertrouwelijkheidaanduiding(self):
        choice_names = VertrouwelijkheidsAanduiding.names
        for choice in choice_names:
            EnkelvoudigInformatieObjectFactory.create(
                vertrouwelijkheidaanduiding=choice
            )

        for choice in choice_names:
            with self.subTest(choice):
                response = self.client.get(
                    reverse(EnkelvoudigInformatieObject),
                    {"vertrouwelijkheidaanduiding": choice},
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()
                self.assertEqual(data["count"], 1)
                self.assertEqual(
                    data["results"][0]["vertrouwelijkheidaanduiding"], choice
                )

    def test_object_type(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio2 = EnkelvoudigInformatieObjectFactory.create()

        ZaakInformatieObjectFactory.create(informatieobject=eio.canonical)
        BesluitInformatieObjectFactory.create(informatieobject=eio2.canonical)

        response = self.client.get(
            reverse(EnkelvoudigInformatieObject),
            {"objectinformatieobjecten__objectType": "zaak"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["titel"], eio.titel)

    def test_locked_filter(self):
        locked_canonical = EnkelvoudigInformatieObjectCanonicalFactory(lock="locked")
        EnkelvoudigInformatieObjectFactory(canonical=locked_canonical)
        EnkelvoudigInformatieObjectFactory()

        with self.subTest("locked_objects"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject), {"locked": True}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["locked"], True)

        with self.subTest("unlocked_objects"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject), {"locked": False}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["locked"], False)

    def test_ordering_filter(self):
        first_information_object = EnkelvoudigInformatieObjectFactory.create(
            auteur="Albert",
            bestandsomvang=10,
            formaat="application/json",
            creatiedatum="2000-01-01",
            status="definitief",
            titel="A",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
        )
        second_information_object = EnkelvoudigInformatieObjectFactory.create(
            auteur="Bernard",
            bestandsomvang=20,
            formaat="application/vnd.api+json",
            creatiedatum="2010-01-01",
            status="gearchiveerd",
            titel="B",
            vertrouwelijkheidaanduiding="confidentieel",
        )
        third_information_object = EnkelvoudigInformatieObjectFactory.create(
            auteur="Calvin",
            bestandsomvang=30,
            formaat="application/xml",
            creatiedatum="2020-01-01",
            status="in_bewerking",
            titel="C",
            vertrouwelijkheidaanduiding="zeer_geheim",
        )

        order_field_options = [
            "auteur",
            "bestandsomvang",
            "formaat",
            "creatiedatum",
            "status",
            "titel",
            "vertrouwelijkheidaanduiding",
        ]

        for order_option in order_field_options:
            with self.subTest(order_option):
                # Testing acending order
                response = self.client.get(
                    reverse(EnkelvoudigInformatieObject), {"ordering": order_option}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()["results"]
                self.assertEqual(
                    data[0][order_option],
                    getattr(first_information_object, order_option),
                )
                self.assertEqual(
                    data[1][order_option],
                    getattr(second_information_object, order_option),
                )
                self.assertEqual(
                    data[2][order_option],
                    getattr(third_information_object, order_option),
                )

                # Testing decending order
                response = self.client.get(
                    reverse(EnkelvoudigInformatieObject),
                    {"ordering": f"-{order_option}"},
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()["results"]
                self.assertEqual(
                    data[0][order_option],
                    getattr(third_information_object, order_option),
                )
                self.assertEqual(
                    data[1][order_option],
                    getattr(second_information_object, order_option),
                )
                self.assertEqual(
                    data[2][order_option],
                    getattr(first_information_object, order_option),
                )

    def test_trefwoorden(self):
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=["foo"])
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=["foo", "bar"])
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=["bar", "baz"])
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=["zzz"])

        with self.subTest("contains"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject), {"trefwoorden": "foo,bar"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["trefwoorden"], ["foo", "bar"])

        with self.subTest("overlap"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"trefwoorden__overlap": "foo,bar"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 3)
            self.assertEqual(data["results"][0]["trefwoorden"], ["foo"])
            self.assertEqual(data["results"][1]["trefwoorden"], ["foo", "bar"])
            self.assertEqual(data["results"][2]["trefwoorden"], ["bar", "baz"])

    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_internal_objectinformatieobjecten_object_filter(self):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        zaak_eio = EnkelvoudigInformatieObjectFactory.create(titel="zaak")
        zaak = ZaakFactory.create()
        ZaakInformatieObjectFactory.create(
            zaak=zaak, informatieobject=zaak_eio.canonical
        )
        zaak_url = reverse(zaak)

        besluit_eio = EnkelvoudigInformatieObjectFactory.create(titel="besluit")
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(
            besluit=besluit, informatieobject=besluit_eio.canonical
        )
        besluit_url = reverse(besluit)

        EnkelvoudigInformatieObjectFactory.create_batch(3)

        with self.subTest("zaak"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {
                    "objectinformatieobjecten__object": f"http://testserver.com{zaak_url}"
                },
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "zaak")

        with self.subTest("besluit"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {
                    "objectinformatieobjecten__object": f"http://testserver.com{besluit_url}"
                },
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "besluit")

    @tag("external-urls")
    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_external_objectinformatieobjecten_object_filter(self):
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaak_eio = EnkelvoudigInformatieObjectFactory.create(titel="zaak")
        ObjectInformatieObject.objects.create(
            informatieobject=zaak_eio.canonical,
            zaak=zaak,
            object_type="zaak",
        )

        besluit = "https://externe.catalogus.nl/api/v1/besluiten/bd0788ea-90b6-4c70-8e14-62f327296c12"
        besluit_eio = EnkelvoudigInformatieObjectFactory.create(titel="besluit")
        ObjectInformatieObject.objects.create(
            informatieobject=besluit_eio.canonical,
            besluit=besluit,
            object_type="besluit",
        )

        verzoek = "https://externe.catalogus.nl/api/v1/verzoeken/41460bca-5ffc-4dbe-b205-468bdc5eac6b"
        verzoek_eio = EnkelvoudigInformatieObjectFactory.create(titel="verzoek")
        ObjectInformatieObject.objects.create(
            informatieobject=verzoek_eio.canonical,
            verzoek=verzoek,
            object_type="verzoek",
        )

        EnkelvoudigInformatieObjectFactory.create_batch(3)

        with self.subTest("zaak"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"objectinformatieobjecten__object": zaak},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "zaak")

        with self.subTest("besluit"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"objectinformatieobjecten__object": besluit},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "besluit")

        with self.subTest("verzoek"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"objectinformatieobjecten__object": verzoek},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["titel"], "verzoek")

    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_internal_informatieobjecttype_filter(self):
        ServiceFactory.create(
            api_root="http://externe.catalogi.com/catalogi/",
            api_type=APITypes.ztc,
        )

        iot = "http://externe.catalogi.com/catalogi/api/v1/informatieobjecttypen/a7a49f9e-3de9-43f0-b2b6-1a59d307f01a"
        EnkelvoudigInformatieObjectFactory.create(informatieobjecttype=iot, titel="one")
        EnkelvoudigInformatieObjectFactory.create(titel="two")
        EnkelvoudigInformatieObjectFactory.create(titel="three")
        EnkelvoudigInformatieObjectFactory.create(titel="four")

        response = self.client.get(
            reverse(EnkelvoudigInformatieObject),
            {"informatieobjecttype": iot},
            headers={"host": "testserver.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["titel"], "one")

    @tag("external-urls")
    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_external_informatieobjecttype_filter(self):
        iot1 = InformatieObjectTypeFactory.create()
        iot2, iot3, iot4 = InformatieObjectTypeFactory.create_batch(3)
        iot1_url = f"http://testserver.com{iot1.get_absolute_api_url()}"

        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iot1, titel="one"
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iot2, titel="two"
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iot3, titel="three"
        )
        EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=iot4, titel="four"
        )

        response = self.client.get(
            reverse(EnkelvoudigInformatieObject),
            {"informatieobjecttype": iot1_url},
            headers={"host": "testserver.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["titel"], "one")


class GebruiksrechtenFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(
            reverse(Gebruiksrechten), {"informatieobject": "bla"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype__concept=False
        )
        GebruiksrechtenFactory.create(informatieobject=eio)

        response = self.client.get(
            reverse(Gebruiksrechten), {"informatieobject": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class ObjectInformatieObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["informatieobject", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ObjectInformatieObject), {query_param: "bla"}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        for query_param in ["informatieobject", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ObjectInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])

    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_internal_object_filter(self):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        zaak_eioc = EnkelvoudigInformatieObjectCanonicalFactory.create()
        zaak = ZaakFactory.create()
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=zaak_eioc)
        zaak_url = reverse(zaak)

        besluit_eioc = EnkelvoudigInformatieObjectCanonicalFactory.create()
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(
            besluit=besluit, informatieobject=besluit_eioc
        )
        besluit_url = reverse(besluit)

        with self.subTest("zaak"):
            response = self.client.get(
                reverse(ObjectInformatieObject),
                {"object": f"http://testserver.com{zaak_url}"},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["objectType"], "zaak")

        with self.subTest("besluit"):
            response = self.client.get(
                reverse(ObjectInformatieObject),
                {"object": f"http://testserver.com{besluit_url}"},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["objectType"], "besluit")

    @tag("external-urls")
    @override_settings(
        ALLOWED_HOSTS=["testserver.com", "openzaak.nl"],
    )
    def test_external_object_filter(self):
        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaak_eioc = EnkelvoudigInformatieObjectCanonicalFactory.create()
        ObjectInformatieObject.objects.create(
            informatieobject=zaak_eioc, zaak=zaak, object_type="zaak"
        )

        besluit = "https://externe.catalogus.nl/api/v1/besluiten/bd0788ea-90b6-4c70-8e14-62f327296c12"
        besluit_eioc = EnkelvoudigInformatieObjectCanonicalFactory.create()
        ObjectInformatieObject.objects.create(
            informatieobject=besluit_eioc,
            besluit=besluit,
            object_type="besluit",
        )

        verzoek = "https://externe.catalogus.nl/api/v1/verzoeken/41460bca-5ffc-4dbe-b205-468bdc5eac6b"
        verzoek_eioc = EnkelvoudigInformatieObjectCanonicalFactory.create()
        ObjectInformatieObject.objects.create(
            informatieobject=verzoek_eioc,
            verzoek=verzoek,
            object_type="verzoek",
        )

        with self.subTest("zaak"):
            response = self.client.get(
                reverse(ObjectInformatieObject),
                {"object": zaak},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["objectType"], "zaak")

        with self.subTest("besluit"):
            response = self.client.get(
                reverse(ObjectInformatieObject),
                {"object": besluit},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["objectType"], "besluit")

        with self.subTest("verzoek"):
            response = self.client.get(
                reverse(ObjectInformatieObject),
                {"object": verzoek},
                headers={"host": "testserver.com"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["objectType"], "verzoek")
