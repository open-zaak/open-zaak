from vng_api_common.models import JWTSecret
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import VertrouwelijkheidsAanduiding, ComponentTypes
from vng_api_common.tests import generate_jwt_auth, reverse
from django.db.models import Model


class JWTAuthMixin:
    """
    Configure the local auth cache.

    Creates the local auth objects for permission checks, as if you're talking
    to a real AC behind the scenes.
    """
    client_id = 'testsuite'
    secret = 'letmein'

    user_id = 'test_user_id'
    user_representation = 'Test User'

    scopes = None
    heeft_alle_autorisaties = False
    component = None
    zaaktype = None
    informatieobjecttype = None
    besluittype = None
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim
    host_prefix = 'http://testserver'

    @classmethod
    def check_for_instance(cls, obj) -> str:
        if isinstance(obj, Model):
            return cls.host_prefix + reverse(obj)
        return obj

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id,
            defaults={'secret': cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label='for test',
            heeft_alle_autorisaties=cls.heeft_alle_autorisaties
        )

        if cls.heeft_alle_autorisaties is False:
            zaaktype_url = cls.check_for_instance(cls.zaaktype)
            besluittype_url = cls.check_for_instance(cls.besluittype)
            informatieobjecttype_url = cls.check_for_instance(cls.informatieobjecttype)

            cls.autorisatie = Autorisatie.objects.create(
                applicatie=cls.applicatie,
                component=cls.component or ComponentTypes.zrc,
                scopes=cls.scopes or [],
                zaaktype=zaaktype_url or '',
                informatieobjecttype=informatieobjecttype_url or '',
                besluittype=besluittype_url or '',
                max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding
            )

    def setUp(self):
        super().setUp()

        token = generate_jwt_auth(
            client_id=self.client_id,
            secret=self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)
