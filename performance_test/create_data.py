from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.tests.factories import ApplicatieFactory
from openzaak.components.catalogi.models import Catalogus
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.zaken.tests.factories import ZaakFactory

catalogus, _ = Catalogus.objects.get_or_create(
    domein="AAAAA", rsin="000000000", defaults={"naam": "catalogus"}
)

zaaktype = ZaakTypeFactory.create(catalogus=catalogus)

JWTSecret.objects.get_or_create(identifier="foo", secret="bar")
ApplicatieFactory.create(client_ids=["foo"], heeft_alle_autorisaties=True)

ZaakFactory.create_batch(
    1000,
    zaaktype=zaaktype,
)
