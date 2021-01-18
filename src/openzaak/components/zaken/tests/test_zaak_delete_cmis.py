# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.tests import reverse

from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

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


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class US349TestCase(JWTAuthMixin, APICMISTestCase, OioMixin):

    heeft_alle_autorisaties = True

    def test_delete_zaak_cascades_properly(self):
        """
        Deleting a zaak causes all related objects to be deleted as well.
        """
        self.create_zaak_besluit_services()
        zaak = self.create_zaak()

        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))

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
