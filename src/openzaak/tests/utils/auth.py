# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import ClassVar, Collection, List, Optional

from django.db.models import Model

from vng_api_common.authorizations.models import AuthorizationsConfig
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.scopes import Scope
from vng_api_common.tests.auth import JWTAuthMixin as _JWTAuthMixin

from openzaak.components.autorisaties.models import Applicatie, Autorisatie
from openzaak.utils.urls import reverse


class JWTAuthMixin:
    """
    Configure the local auth cache.

    Creates the local auth objects for permission checks, as if you're talking
    to a real AC behind the scenes.
    """

    client_id = "testsuite"
    secret = "bab8d686-5d86-4de4-9794-2b18426ea303"

    user_id = "test_user_id"
    user_representation = "Test User"

    scopes: Collection[Scope] | None = None
    heeft_alle_autorisaties = False
    component: ComponentTypes | None = None
    zaaktype: Model | None = None
    informatieobjecttype: Model | None = None
    besluittype: Model | None = None
    max_vertrouwelijkheidaanduiding: VertrouwelijkheidsAanduiding = (
        VertrouwelijkheidsAanduiding.zeer_geheim
    )
    host_prefix = "http://testserver"

    applicatie: ClassVar[Applicatie]
    autorisatie: ClassVar[Autorisatie]

    @classmethod
    def check_for_instance(cls, obj) -> str:
        if isinstance(obj, Model):
            return cls.host_prefix + reverse(obj)
        return obj

    @classmethod
    def setUpTestData(cls):
        if hasattr(super(), "setUpTestData"):
            super().setUpTestData()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id, defaults={"secret": cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label="for test",
            heeft_alle_autorisaties=cls.heeft_alle_autorisaties,
        )

        if cls.heeft_alle_autorisaties is False:
            cls.autorisatie = Autorisatie.objects.create(
                applicatie=cls.applicatie,
                component=cls.component or ComponentTypes.zrc,
                scopes=cls.scopes or [],
                zaaktype=cls.zaaktype,
                informatieobjecttype=cls.informatieobjecttype,
                besluittype=cls.besluittype,
                max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
            )

    def setUp(self):
        super().setUp()

        token = generate_jwt(
            self.client_id,
            self.secret,
            self.user_id,
            self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)


class JWTAuthCacheMixin(_JWTAuthMixin):
    # TODO add docstring
    @staticmethod
    def _create_credentials(
        client_id: str,
        secret: str,
        heeft_alle_autorisaties: bool,
        max_vertrouwelijkheidaanduiding: str,
        scopes: Optional[List[str]] = None,
        zaaktype: Optional[str] = None,
        informatieobjecttype: Optional[str] = None,
        besluittype: Optional[str] = None,
    ):
        JWTSecret.objects.get_or_create(
            identifier=client_id, defaults={"secret": secret}
        )

        config = AuthorizationsConfig.get_solo()

        applicatie = Applicatie.objects.create(
            client_ids=[client_id],
            label="for test",
            heeft_alle_autorisaties=heeft_alle_autorisaties,
        )

        if heeft_alle_autorisaties is False:
            autorisatie = Autorisatie.objects.create(
                applicatie=applicatie,
                component=config.component,
                scopes=scopes or [],
                zaaktype=zaaktype or "",
                informatieobjecttype=informatieobjecttype or "",
                besluittype=besluittype or "",
                max_vertrouwelijkheidaanduiding=max_vertrouwelijkheidaanduiding,
            )
        else:
            autorisatie = None

        return applicatie, autorisatie
