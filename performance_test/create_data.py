from vng_api_common.models import JWTSecret

from openzaak.components.autorisaties.tests.factories import (
    ApplicatieFactory,
    AutorisatieFactory,
)
from openzaak.components.catalogi.models import Catalogus
from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.components.zaken.tests.factories import ZaakFactory

catalogus, _ = Catalogus.objects.get_or_create(
    domein="AAAAA", rsin="000000000", defaults={"naam": "catalogus"}
)

zaaktype = ZaakTypeFactory.create(catalogus=catalogus)
zaaktype2 = ZaakTypeFactory.create(catalogus=catalogus)

JWTSecret.objects.get_or_create(identifier="foo", secret="bar")
ApplicatieFactory.create(client_ids=["foo"], heeft_alle_autorisaties=True)

JWTSecret.objects.get_or_create(identifier="non_superuser", secret="non_superuser")
applicatie = ApplicatieFactory.create(
    client_ids=["non_superuser"], heeft_alle_autorisaties=False
)
AutorisatieFactory.create(
    applicatie=applicatie,
    component="zrc",
    scopes=["zaken.lezen"],
    max_vertrouwelijkheidaanduiding="zeer_geheim",
    zaaktype=f"http://localhost:8000/catalogi/api/v1/zaaktypen/{zaaktype.uuid}",
)
AutorisatieFactory.create(
    applicatie=applicatie,
    component="zrc",
    scopes=["zaken.lezen"],
    max_vertrouwelijkheidaanduiding="zeer_geheim",
    zaaktype=f"http://localhost:8000/catalogi/api/v1/zaaktypen/{zaaktype2.uuid}",
)

ZaakFactory.create_batch(
    2000,
    zaaktype=zaaktype,
)
ZaakFactory.create_batch(
    1000,
    zaaktype=zaaktype2,
)
ZaakFactory.create_batch(
    500,
)
