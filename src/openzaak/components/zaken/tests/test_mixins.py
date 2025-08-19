# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import datetime
from unittest.mock import Mock

from rest_framework import serializers, viewsets
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.versioning import URLPathVersioning
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.serializers import CachedHyperlinkedRelatedField
from vng_api_common.tests import reverse

from openzaak.components.autorisaties.middleware import JWTAuth
from openzaak.components.zaken.api.exceptions import ZaakClosed
from openzaak.components.zaken.api.mixins import ClosedZaakMixin
from openzaak.components.zaken.api.scopes import SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN
from openzaak.components.zaken.models import Zaak
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin

factory = APIRequestFactory()
REQUEST = factory.get("/")
REQUEST.versioning_scheme = URLPathVersioning()
REQUEST.version = "1"


class RelatedModelSerializer(serializers.Serializer):
    zaak = CachedHyperlinkedRelatedField(
        queryset=Zaak.objects.all(),
        view_name="zaak-detail",
        lookup_field="uuid",
        allow_null=True,
    )


class GenericViewSet(viewsets.GenericViewSet):
    def perform_create(self, serializer):
        return

    def perform_update(self, serializer):
        return

    def perform_destroy(self, instance):
        return


class RelatedViewSet(ClosedZaakMixin, GenericViewSet):
    queryset = Mock()
    queryset.model = Mock()
    queryset.model._meta = Mock(app_label="zaken")
    serializer_class = RelatedModelSerializer


class ClosedZaakMixinTests(JWTAuthMixin, APITestCase):
    def setUp(self):
        super().setUp()

        self.zaak = ZaakFactory()
        self.token = generate_jwt(
            self.client_id, self.secret, None, self.user_representation
        )

        self.viewset = RelatedViewSet()
        self.viewset.request = Request(REQUEST)
        self.viewset.request.jwt_auth = JWTAuth(self.token.split(" ")[1])

    def test_check_zaak_is_none(self):
        serializer = RelatedModelSerializer(data={"zaak": None})
        serializer.is_valid(raise_exception=True)

        self.viewset.perform_create(serializer)

    def test_check_zaak_is_not_closed(self):
        self.assertFalse(self.zaak.is_closed)

        serializer = RelatedModelSerializer(data={"zaak": reverse(self.zaak)})
        serializer.is_valid(raise_exception=True)

        self.viewset.perform_create(serializer)

    def test_check_zaak_has_permissions(self):
        self.assertFalse(self.zaak.is_closed)

        self.zaak.einddatum = datetime.date(2025, 1, 1)
        self.zaak.vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
        self.zaak.save()
        autorisatie = Autorisatie.objects.get()
        autorisatie.zaaktype = f"http://testserver{reverse(self.zaak.zaaktype)}"
        autorisatie.scopes.append(SCOPE_ZAKEN_GEFORCEERD_BIJWERKEN)
        autorisatie.save()

        self.assertTrue(self.zaak.is_closed)

        serializer = RelatedModelSerializer(data={"zaak": reverse(self.zaak)})
        serializer.is_valid(raise_exception=True)

        self.viewset.perform_create(serializer)

    def test_check_zaak_has_not_permissions(self):
        self.assertFalse(self.zaak.is_closed)
        self.zaak.einddatum = datetime.date(2025, 1, 1)
        self.zaak.save()
        self.assertTrue(self.zaak.is_closed)

        serializer = RelatedModelSerializer(data={"zaak": reverse(self.zaak)})
        serializer.is_valid(raise_exception=True)

        with self.assertRaises(ZaakClosed):
            self.viewset.perform_create(serializer)
