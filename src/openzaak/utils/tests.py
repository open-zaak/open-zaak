import contextlib
import hashlib
import json
import sys

from django.core.cache import caches
from django.db.models import Model

from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.notifications.models import NotificationsConfig
from vng_api_common.tests import generate_jwt_auth, reverse
from zds_client.tests.mocks import MockClient
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.accounts.models import User
from openzaak.selectielijst.models import ReferentieLijstConfig


class JWTAuthMixin:
    """
    Configure the local auth cache.

    Creates the local auth objects for permission checks, as if you're talking
    to a real AC behind the scenes.
    """

    client_id = "testsuite"
    secret = "letmein"

    user_id = "test_user_id"
    user_representation = "Test User"

    scopes = None
    heeft_alle_autorisaties = False
    component = None
    zaaktype = None
    informatieobjecttype = None
    besluittype = None
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim
    host_prefix = "http://testserver"

    @classmethod
    def check_for_instance(cls, obj) -> str:
        if isinstance(obj, Model):
            return cls.host_prefix + reverse(obj)
        return obj

    @classmethod
    def setUpTestData(cls):
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
            zaaktype_url = cls.check_for_instance(cls.zaaktype)
            besluittype_url = cls.check_for_instance(cls.besluittype)
            informatieobjecttype_url = cls.check_for_instance(cls.informatieobjecttype)

            cls.autorisatie = Autorisatie.objects.create(
                applicatie=cls.applicatie,
                component=cls.component or ComponentTypes.zrc,
                scopes=cls.scopes or [],
                zaaktype=zaaktype_url or "",
                informatieobjecttype=informatieobjecttype_url or "",
                besluittype=besluittype_url or "",
                max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
            )

    def setUp(self):
        super().setUp()

        token = generate_jwt_auth(
            client_id=self.client_id,
            secret=self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)


class ClearCachesMixin:
    def setUp(self):
        self._clear_caches()
        self.addCleanup(self._clear_caches)

    def _clear_caches(self):
        for cache in caches.all():
            cache.clear()


class AdminTestMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = User.objects.create_superuser(
            username="demo",
            email="demo@demo.com",
            password="demo",
            first_name="first",
            last_name="last",
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.login(username="demo", password="demo")

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()


no_fetch = object()


@contextlib.contextmanager
def mock_client(responses: dict):
    try:
        from django.test import override_settings
    except ImportError as exc:
        raise ImportError("You can only use this in a django context") from exc

    try:
        json_string = json.dumps(responses).encode("utf-8")
        md5 = hashlib.md5(json_string).hexdigest()
        name = f"MockClient{md5}"
        # create the class
        type(name, (MockClient,), {"responses": responses})
        dotted_path = f"zds_client.tests.mocks.{name}"
        with override_settings(ZGW_CONSUMERS_CLIENT_CLASS=dotted_path):
            yield

        # clean up
        delattr(sys.modules["zds_client.tests.mocks"], name)
    finally:
        pass


class NotificationServiceMixin:
    def setUp(self):
        super().setUp()

        config = NotificationsConfig.get_solo()
        Service.objects.create(
            api_type=APITypes.nrc,
            api_root=config.api_root,
            client_id="test",
            secret="test",
            user_id="test",
            user_representation="Test",
        )


class ReferentieLijstServiceMixin:
    def setUp(self):
        super().setUp()
        config = ReferentieLijstConfig.get_solo()
        Service.objects.create(
            api_type=APITypes.orc,
            api_root=config.api_root,
            client_id="test",
            secret="test",
            user_id="test",
            user_representation="Test",
        )
