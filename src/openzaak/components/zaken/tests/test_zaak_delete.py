from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, reverse

from openzaak.components.zaken.api.tests.utils import get_operation_url
from openzaak.components.zaken.models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)
from openzaak.components.zaken.models.tests.factories import (
    KlantContactFactory,
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from openzaak.components.zaken.tests.utils import ZAAK_READ_KWARGS

from .utils import ZAAK_WRITE_KWARGS


class US349TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_delete_zaak_cascades_properly(self):
        """
        Deleting a zaak causes all related objects to be deleted as well.
        """
        zaak = ZaakFactory.create()

        ZaakFactory.create(hoofdzaak=zaak)

        ZaakEigenschapFactory.create(zaak=zaak)
        StatusFactory.create(zaak=zaak)
        RolFactory.create(zaak=zaak)
        ResultaatFactory.create(zaak=zaak)
        ZaakObjectFactory.create(zaak=zaak)
        ZaakInformatieObjectFactory.create(zaak=zaak)
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

    def test_delete_deel_zaak(self):
        """
        Deleting a deel zaak only deletes the deel zaak, and not the hoofd zaak.
        """
        zaak = ZaakFactory.create()
        deel_zaak = ZaakFactory.create(hoofdzaak=zaak)

        zaak_delete_url = get_operation_url("zaak_delete", uuid=deel_zaak.uuid)

        response = self.client.delete(zaak_delete_url, **ZAAK_WRITE_KWARGS)
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        self.assertEqual(Zaak.objects.all().count(), 1)
        self.assertEqual(Zaak.objects.get().pk, zaak.pk)

    def test_zaak_with_result(self):
        """
        Test that the zaak-detail correctly contains the URL to the result.
        """
        zaak = ZaakFactory.create()
        resultaat = ResultaatFactory.create(zaak=zaak)
        zaak_url = "http://testserver{path}".format(path=reverse(zaak))
        resultaat_url = "http://testserver{path}".format(path=reverse(resultaat))

        response = self.client.get(zaak_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["resultaat"], resultaat_url)
