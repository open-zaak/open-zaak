# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings

from rest_framework import status
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.tests.utils import APICMISTransactionTestCase, JWTAuthMixin, require_cmis

from ...documenten.tests.factories import EnkelvoudigInformatieObjectFactory
from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from .factories import (
    KlantContactFactory,
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


@require_cmis
@override_settings(CMIS_ENABLED=True)
class US349TestCase(JWTAuthMixin, APICMISTransactionTestCase):
    heeft_alle_autorisaties = True
    base = "https://external.documenten.nl/api/v1/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Service.objects.update_or_create(
            api_root=cls.base,
            defaults=dict(
                slug=cls.base,
                api_type=APITypes.drc,
                label="external documents",
                auth_type=AuthTypes.no_auth,
            ),
        )

        cls.setUpTestData()

    def test_delete_zaak_cascades_properly(self):
        """
        Deleting a zaak causes all related objects to be deleted as well.
        """
        zaak = ZaakFactory.create()

        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakFactory.create(hoofdzaak=zaak)

        ZaakEigenschapFactory.create(zaak=zaak)
        StatusFactory.create(zaak=zaak)
        RolFactory.create(zaak=zaak)
        ResultaatFactory.create(zaak=zaak)
        ZaakObjectFactory.create(zaak=zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        KlantContactFactory.create(zaak=zaak)

        zaak_delete_url = get_operation_url("zaak_delete", uuid=zaak.uuid)

        response = self.client.delete(zaak_delete_url, **ZAAK_WRITE_KWARGS)
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        self.assertEqual(Zaak.objects.all().count(), 0)

        self.assertEqual(ZaakEigenschap.objects.all().count(), 0)
        self.assertEqual(Status.objects.all().count(), 0)
        self.assertEqual(Rol.objects.all().count(), 0)
        self.assertEqual(Resultaat.objects.all().count(), 0)
        self.assertEqual(ZaakObject.objects.all().count(), 0)
        self.assertEqual(ZaakInformatieObject.objects.all().count(), 0)
        self.assertEqual(KlantContact.objects.all().count(), 0)
