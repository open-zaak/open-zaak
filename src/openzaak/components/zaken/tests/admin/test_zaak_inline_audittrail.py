from datetime import datetime

from django.urls import reverse
from django.utils.timezone import make_aware

from django_webtest import WebTest
from vng_api_common.audittrails.models import AuditTrail

from openzaak.accounts.tests.factories import SuperUserFactory
from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    ZaakEigenschap,
    ZaakInformatieObject,
    ZaakObject,
)

from ..factories import (
    KlantContactFactory,
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakObjectFactory,
)
from ..utils import get_operation_url


class ZaakAdminInlineTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = SuperUserFactory.create()
        cls.zaak = ZaakFactory.create()

    def setUp(self):
        super().setUp()

        self.app.set_user(self.user)
        self.zaak_url = get_operation_url("zaak_read", uuid=self.zaak.uuid)
        self.change_url = reverse("admin:zaken_zaak_change", args=(self.zaak.pk,))

    def assertZaakAudittrail(self, audittrail):
        self.assertEqual(audittrail.bron, "ZRC")
        self.assertEqual(audittrail.resultaat, 0)
        self.assertEqual(audittrail.applicatie_weergave, "admin")
        self.assertEqual(audittrail.gebruikers_id, f"{self.user.id}"),
        self.assertEqual(audittrail.gebruikers_weergave, self.user.get_full_name()),
        self.assertEqual(audittrail.hoofd_object, f"http://testserver{self.zaak_url}"),

    def test_status_delete(self):
        status = StatusFactory.create(zaak=self.zaak)
        status_url = get_operation_url("status_read", uuid=status.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["status_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(Status.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(status.uuid))

    def test_status_change(self):
        status = StatusFactory.create(
            zaak=self.zaak, datum_status_gezet=make_aware(datetime(2018, 1, 1))
        )
        status_url = get_operation_url("status_read", uuid=status.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["status_set-0-datum_status_gezet_0"] = "01-01-2019"
        form.submit()

        status.refresh_from_db()
        self.assertEqual(status.datum_status_gezet, make_aware(datetime(2019, 1, 1)))

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["datum_status_gezet"], "2018-01-01T00:00:00Z")
        self.assertEqual(new_data["datum_status_gezet"], "2019-01-01T00:00:00Z")

    def test_status_add(self):
        statustype = StatusTypeFactory.create(zaaktype=self.zaak.zaaktype)

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["status_set-0-statustype"] = statustype.id
        form["status_set-0-datum_status_gezet_0"] = "01-01-2019"
        form["status_set-0-datum_status_gezet_1"] = "10:00:00"
        form["status_set-0-statustoelichting"] = "desc"
        form.submit()

        self.assertEqual(Status.objects.count(), 1)

        status = Status.objects.get()
        status_url = get_operation_url("status_read", uuid=status.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "status"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{status_url}"),
        self.assertEqual(audittrail.resource_weergave, status.unique_representation())
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(status.uuid))

    def test_rol_delete(self):
        rol = RolFactory.create(zaak=self.zaak)
        rol_url = get_operation_url("rol_read", uuid=rol.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["rol_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(Rol.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(rol.uuid))

    def test_rol_change(self):
        rol = RolFactory.create(zaak=self.zaak, roltoelichting="old")
        rol_url = get_operation_url("rol_read", uuid=rol.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["rol_set-0-roltoelichting"] = "new"
        form.submit()

        rol.refresh_from_db()
        self.assertEqual(rol.roltoelichting, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation()),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["roltoelichting"], "old")
        self.assertEqual(new_data["roltoelichting"], "new")

    def test_rol_add(self):
        roltype = RolTypeFactory.create(zaaktype=self.zaak.zaaktype)

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["rol_set-0-roltype"] = roltype.id
        form["rol_set-0-betrokkene_type"] = "vestiging"
        form["rol_set-0-roltoelichting"] = "desc"
        form.submit()

        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()
        rol_url = get_operation_url("rol_read", uuid=rol.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "rol"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{rol_url}"),
        self.assertEqual(audittrail.resource_weergave, rol.unique_representation())
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(rol.uuid))

    def test_klantcontact_delete(self):
        klantcontact = KlantContactFactory.create(zaak=self.zaak)
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["klantcontact_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(KlantContact.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(klantcontact.uuid))

    def test_klantcontact_change(self):
        klantcontact = KlantContactFactory.create(zaak=self.zaak, identificatie="old")
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["klantcontact_set-0-identificatie"] = "new"
        form.submit()

        klantcontact.refresh_from_db()
        self.assertEqual(klantcontact.identificatie, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["identificatie"], "old")
        self.assertEqual(new_data["identificatie"], "new")

    def test_klantcontact_add(self):
        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["klantcontact_set-0-identificatie"] = "12345"
        form["klantcontact_set-0-datumtijd_0"] = "01-01-2019"
        form["klantcontact_set-0-datumtijd_1"] = "10:00:00"
        form.submit()

        self.assertEqual(KlantContact.objects.count(), 1)

        klantcontact = KlantContact.objects.get()
        klantcontact_url = get_operation_url(
            "klantcontact_read", uuid=klantcontact.uuid
        )
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "klantcontact"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{klantcontact_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, klantcontact.unique_representation()
        )
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(klantcontact.uuid))

    def test_zaakobject_delete(self):
        zaakobject = ZaakObjectFactory.create(zaak=self.zaak)
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakobject_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(ZaakObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(zaakobject.uuid))

    def test_zaakobject_change(self):
        zaakobject = ZaakObjectFactory.create(zaak=self.zaak, relatieomschrijving="old")
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakobject_set-0-object_type"] = "adres"
        form["zaakobject_set-0-relatieomschrijving"] = "new"

        form.submit()

        zaakobject.refresh_from_db()
        self.assertEqual(zaakobject.relatieomschrijving, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["relatieomschrijving"], "old")
        self.assertEqual(new_data["relatieomschrijving"], "new")

    def test_zaakobject_add(self):
        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["zaakobject_set-0-object_type"] = "adres"
        form["zaakobject_set-0-relatieomschrijving"] = "new"
        form.submit()

        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()
        zaakobject_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "zaakobject"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{zaakobject_url}"),
        self.assertEqual(
            audittrail.resource_weergave, zaakobject.unique_representation()
        )
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(zaakobject.uuid))

    def test_zaakeigenschap_delete(self):
        zaakeigenschap = ZaakEigenschapFactory.create(zaak=self.zaak)
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read", uuid=zaakeigenschap.uuid, zaak_uuid=self.zaak.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakeigenschap_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(ZaakEigenschap.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(zaakeigenschap.uuid))

    def test_zaakeigenschap_change(self):
        zaakeigenschap = ZaakEigenschapFactory.create(zaak=self.zaak, _naam="old")
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read", uuid=zaakeigenschap.uuid, zaak_uuid=self.zaak.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakeigenschap_set-0-_naam"] = "new"
        form.submit()

        zaakeigenschap.refresh_from_db()
        self.assertEqual(zaakeigenschap._naam, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw

        self.assertEqual(old_data["naam"], "old")
        self.assertEqual(new_data["naam"], "new")

    def test_zaakeigenschap_add(self):
        eigenschap = EigenschapFactory.create(zaaktype=self.zaak.zaaktype)

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["zaakeigenschap_set-0-eigenschap"] = eigenschap.id
        form["zaakeigenschap_set-0-_naam"] = "some name"
        form["zaakeigenschap_set-0-waarde"] = "desc"
        form.submit()

        self.assertEqual(ZaakEigenschap.objects.count(), 1)

        zaakeigenschap = ZaakEigenschap.objects.get()
        zaakeigenschap_url = get_operation_url(
            "zaakeigenschap_read", uuid=zaakeigenschap.uuid, zaak_uuid=self.zaak.uuid
        )
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "zaakeigenschap"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakeigenschap_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakeigenschap.unique_representation()
        )
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(zaakeigenschap.uuid))

    def test_zaakinformatieobject_delete(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create(zaak=self.zaak)
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakinformatieobject_set-0-DELETE"] = True
        form.submit()

        self.assertEqual(ZaakInformatieObject.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(zaakinformatieobject.uuid))

    def test_zaakinformatieobject_change(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create(
            zaak=self.zaak, beschrijving="old"
        )
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["zaakinformatieobject_set-0-beschrijving"] = "new"
        form.submit()

        zaakinformatieobject.refresh_from_db()
        self.assertEqual(zaakinformatieobject.beschrijving, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["beschrijving"], "old")
        self.assertEqual(new_data["beschrijving"], "new")

    def test_zaakinformatieobject_add(self):
        informatieobject = EnkelvoudigInformatieObjectFactory.create()

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form[
            "zaakinformatieobject_set-0-_informatieobject"
        ] = informatieobject.canonical.id
        form["zaakinformatieobject_set-0-aard_relatie"] = "hoort_bij"
        form["zaakinformatieobject_set-0-beschrijving"] = "desc"
        form.submit()

        self.assertEqual(ZaakInformatieObject.objects.count(), 1)

        zaakinformatieobject = ZaakInformatieObject.objects.get()
        zaakinformatieobject_url = get_operation_url(
            "zaakinformatieobject_read", uuid=zaakinformatieobject.uuid
        )
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "zaakinformatieobject"),
        self.assertEqual(
            audittrail.resource_url, f"http://testserver{zaakinformatieobject_url}"
        ),
        self.assertEqual(
            audittrail.resource_weergave, zaakinformatieobject.unique_representation()
        )
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(zaakinformatieobject.uuid))

    def test_resultaat_delete(self):
        resultaat = ResultaatFactory.create(zaak=self.zaak)
        resultaat_url = get_operation_url("resultaat_read", uuid=resultaat.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["resultaat-0-DELETE"] = True
        form.submit()

        self.assertEqual(Resultaat.objects.count(), 0)

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "destroy")
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),
        self.assertEqual(audittrail.nieuw, None)

        old_data = audittrail.oud
        self.assertEqual(old_data["uuid"], str(resultaat.uuid))

    def test_resultaat_change(self):
        resultaat = ResultaatFactory.create(zaak=self.zaak, toelichting="old")
        resultaat_url = get_operation_url("resultaat_read", uuid=resultaat.uuid)

        get_response = self.app.get(self.change_url)

        form = get_response.form
        form["resultaat-0-toelichting"] = "new"
        form.submit()

        resultaat.refresh_from_db()
        self.assertEqual(resultaat.toelichting, "new")

        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "update")
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        ),

        old_data, new_data = audittrail.oud, audittrail.nieuw
        self.assertEqual(old_data["toelichting"], "old")
        self.assertEqual(new_data["toelichting"], "new")

    def test_resultaat_add(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype=self.zaak.zaaktype)

        get_response = self.app.get(self.change_url)
        form = get_response.form

        form["resultaat-0-_resultaattype"] = resultaattype.id
        form["resultaat-0-toelichting"] = "desc"
        form.submit()

        self.assertEqual(Resultaat.objects.count(), 1)

        resultaat = Resultaat.objects.get()
        resultaat_url = get_operation_url("resultaat_read", uuid=resultaat.uuid)
        audittrail = AuditTrail.objects.get()

        self.assertZaakAudittrail(audittrail)
        self.assertEqual(audittrail.actie, "create")
        self.assertEqual(audittrail.resource, "resultaat"),
        self.assertEqual(audittrail.resource_url, f"http://testserver{resultaat_url}"),
        self.assertEqual(
            audittrail.resource_weergave, resultaat.unique_representation()
        )
        self.assertEqual(audittrail.oud, None)

        new_data = audittrail.nieuw
        self.assertEqual(new_data["uuid"], str(resultaat.uuid))
