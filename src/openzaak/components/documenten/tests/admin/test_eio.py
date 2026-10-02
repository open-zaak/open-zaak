# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from unittest.mock import patch

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings, tag
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from privates.test import temp_private_root
from webtest import Upload

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.admin import (
    EnkelvoudigInformatieObjectAdmin,
    EnkelvoudigInformatieObjectForm,
)
from openzaak.components.documenten.exceptions import DocumentBackendNotImplementedError
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
)
from openzaak.components.documenten.widgets import PrivateFileWidget
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils.admin import AdminTestMixin

from ..factories import EnkelvoudigInformatieObjectCanonicalFactory


@disable_admin_mfa()
class EnkelvoudigInformatieObjectAdminTests(AdminTestMixin, WebTest):
    def test_form_widget(self):
        admin_obj = EnkelvoudigInformatieObjectAdmin(
            EnkelvoudigInformatieObject, admin.site
        )
        form = admin_obj.get_form(None)()
        self.assertIsInstance(form.fields["inhoud"].widget, PrivateFileWidget)

    @override_settings(DOCUMENTEN_API_BACKEND="test")
    def test_form_widget_not_implemented_documenten_api_backend(self):
        with self.assertRaises(DocumentBackendNotImplementedError):
            admin_obj = EnkelvoudigInformatieObjectAdmin(
                EnkelvoudigInformatieObject, admin.site
            )
            admin_obj.get_form(None)()

    def test_add_informatieobject_page(self):
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        self.assertEqual(response.status_code, 200)

    def test_create_informatieobject_save(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.forms["enkelvoudiginformatieobject_form"]

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"foo")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 302)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.canonical, canonical)
        self.assertEqual(eio.inhoud.read(), b"foo")

    @tag("gh-2530")
    @temp_private_root()
    def test_create_informatieobject_with_long_inhoud_filename(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        response = self.app.get(
            reverse("admin:documenten_enkelvoudiginformatieobject_add")
        )
        form = response.forms["enkelvoudiginformatieobject_form"]
        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload(f"{'a' * 251}.pdf", b"document")

        response = form.submit(name="_continue")

        self.assertEqual(response.status_code, 302)
        document = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(document.inhoud.name.rsplit("/", 1)[-1], f"{'a' * 243}.pdf")
        self.assertEqual(document.inhoud.read(), b"document")

    @tag("gh-1306")
    def test_create_informatieobject_save_identificatie_all_characters_allowed(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.forms["enkelvoudiginformatieobject_form"]

        form["identificatie"] = "some docüment"
        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["_informatieobjecttype"] = informatieobjecttype.pk
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"foo")

        response = form.submit(name="_continue")
        self.assertEqual(response.status_code, 302)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.identificatie, "some docüment")

    def test_create_without_iotype(self):
        """
        regression test for https://github.com/open-zaak/open-zaak/issues/1441
        """
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version=None
        )
        add_url = reverse("admin:documenten_enkelvoudiginformatieobject_add")

        response = self.app.get(add_url)
        form = response.forms["enkelvoudiginformatieobject_form"]

        form["canonical"] = canonical.pk
        form["bronorganisatie"] = "000000000"
        form["creatiedatum"] = "2010-01-01"
        form["titel"] = "test"
        form["auteur"] = "test"
        form["taal"] = "nld"
        form["inhoud"] = Upload("stuff.txt", b"some content")

        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Je moet een informatieobjecttype opgeven", response.text)

    def test_delete_without_references(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()

        eio = canonical.latest_version

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete", args=(eio.pk,)
        )
        response = self.app.get(url)
        form = response.forms[1]
        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 0)
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)

    def test_delete_without_references_locked(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=True)

        eio = canonical.latest_version

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete", args=(eio.pk,)
        )
        response = self.app.get(url)
        form = response.forms[1]
        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)

        self.assertInHTML(
            _("Gelockte objecten mogen niet worden verwijderd"),
            response.content.decode("utf-8"),
        )

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 1)

    def test_delete_with_references(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create()

        eio = canonical.latest_version

        ZaakInformatieObjectFactory.create(informatieobject=canonical)

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete", args=(eio.pk,)
        )
        response = self.app.get(url)
        form = response.forms[1]
        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)

        self.assertInHTML(
            _(
                "All relations to the document must be destroyed before destroying the document"
            ),
            response.content.decode("utf-8"),
        )

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 1)

    def test_delete_with_canonical_locK(self):
        canonical = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=True)

        eio = canonical.latest_version

        url = reverse(
            "admin:documenten_enkelvoudiginformatieobject_delete", args=(eio.pk,)
        )
        response = self.app.get(url)
        form = response.forms[1]
        response = form.submit().follow()

        self.assertEqual(response.status_code, 200)

        self.assertInHTML(
            _("Locked objects cannot be destroyed"),
            response.content.decode("utf-8"),
        )

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 1)


@disable_admin_mfa()
class EnkelvoudigInformatieObjectCanonicalAdminTests(AdminTestMixin, WebTest):
    def test_eio_add_no_version(self):
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)

        add_url = reverse("admin:documenten_enkelvoudiginformatieobjectcanonical_add")
        get_response = self.app.get(add_url)
        form = get_response.forms["enkelvoudiginformatieobjectcanonical_form"]
        response = form.submit()
        self.assertEqual(response.status_code, 200)

        version_form = response.context["inline_admin_formsets"][0].forms[0]

        self.assertEqual(
            version_form.errors["bronorganisatie"], [_("This field is required.")]
        )
        self.assertEqual(
            version_form.errors["creatiedatum"], [_("This field is required.")]
        )
        self.assertEqual(version_form.errors["titel"], [_("This field is required.")])
        self.assertEqual(version_form.errors["auteur"], [_("This field is required.")])
        self.assertEqual(version_form.errors["taal"], [_("This field is required.")])
        self.assertEqual(
            version_form.errors["bestandsomvang"], [_("This field is required.")]
        )
        self.assertEqual(version_form.errors["inhoud"], [_("This field is required.")])
        self.assertEqual(
            version_form.errors["__all__"],
            [
                _("Constraint “%(name)s” is violated.")
                % {
                    "name": "documenten_enkelvoudiginformatieobject__informatieobjecttype_or"
                    "__informatieobjecttype_base_url_filled"
                }
            ],
        )
        # should still be zero
        self.assertEqual(EnkelvoudigInformatieObjectCanonical.objects.count(), 0)


@temp_private_root()
@tag("gh-2530")
class EnkelvoudigInformatieObjectFormInhoudFilenameTests(SimpleTestCase):
    def setUp(self):
        connection_check = patch(
            "openzaak.components.documenten.admin.documenten_storage.connection_check",
            return_value=True,
        )
        connection_check.start()
        self.addCleanup(connection_check.stop)

    def test_short_filename_is_unchanged(self):
        upload = SimpleUploadedFile("report.pdf", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, "report.pdf")

    def test_247_character_filename_is_unchanged(self):
        filename = f"{'a' * 243}.pdf"  # 247 characters including the extension.
        upload = SimpleUploadedFile(filename, b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, filename)

    def test_248_character_filename_is_shortened_to_247(self):
        upload = SimpleUploadedFile(f"{'a' * 244}.pdf", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, f"{'a' * 243}.pdf")
        self.assertEqual(len(cleaned_upload.name), 247)

    def test_255_character_filename_is_shortened_to_247(self):
        upload = SimpleUploadedFile(f"{'a' * 251}.pdf", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, f"{'a' * 243}.pdf")
        self.assertEqual(cleaned_upload.read(), b"inhound-document")

    def test_longer_extension_leaves_less_room_for_name(self):
        # 250 name characters + 5 extension characters = 255
        upload = SimpleUploadedFile(f"{'a' * 250}.docx", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        # Keep the full extension: 242 + 5 = 247
        self.assertEqual(cleaned_upload.name, f"{'a' * 242}.docx")
        self.assertEqual(len(cleaned_upload.name), 247)

    def test_uppercase_extension_is_preserved(self):
        upload = SimpleUploadedFile(f"{'a' * 251}.PDF", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, f"{'a' * 243}.PDF")

    def test_duplicate_long_filename_gets_suffix_without_overwriting(self):
        filename = f"{'a' * 251}.pdf"
        first = EnkelvoudigInformatieObject()
        second = EnkelvoudigInformatieObject()

        for document, content in ((first, b"first upload"), (second, b"second upload")):
            upload = SimpleUploadedFile(filename, content)
            form = EnkelvoudigInformatieObjectForm(instance=document)
            form.cleaned_data = {"inhoud": upload}
            cleaned_upload = form.clean_inhoud()
            EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
                cleaned_upload
            )
            document.inhoud.save(cleaned_upload.name, cleaned_upload, save=False)

        first_name = first.inhoud.name.rsplit("/", 1)[-1]
        second_name = second.inhoud.name.rsplit("/", 1)[-1]
        self.assertEqual(first_name, f"{'a' * 243}.pdf")
        self.assertTrue(second_name.startswith(f"{'a' * 243}_"))
        self.assertTrue(second_name.endswith(".pdf"))
        self.assertEqual(len(second_name), 255)
        with first.inhoud.open("rb") as stored_file:
            self.assertEqual(stored_file.read(), b"first upload")
        with second.inhoud.open("rb") as stored_file:
            self.assertEqual(stored_file.read(), b"second upload")

    def test_name_with_multiple_dots_keeps_final_extension(self):
        upload = SimpleUploadedFile(f"test.{'a' * 245}.pdf", b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        # 5 characters for "test." + 238 for the name + 4 for ".pdf" = 247.
        self.assertEqual(cleaned_upload.name, f"test.{'a' * 238}.pdf")
        self.assertEqual(len(cleaned_upload.name), 247)

    def test_name_without_extension_is_shortened(self):
        upload = SimpleUploadedFile("a" * 255, b"inhound-document")
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": upload}

        cleaned_upload = form.clean_inhoud()
        EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
            cleaned_upload
        )

        self.assertEqual(cleaned_upload.name, "a" * 247)

    def test_filename_longer_than_255_characters_is_rejected(self):
        upload = SimpleUploadedFile("test.pdf", b"inhound-document")
        upload._name = "a" * 256
        form = EnkelvoudigInformatieObjectForm()

        with self.assertRaises(ValidationError) as context:
            form.cleaned_data = {"inhoud": upload}
            EnkelvoudigInformatieObject._meta.get_field("inhoud").run_validators(
                form.clean_inhoud()
            )

        self.assertIn(
            "De bestandsnaam van de inhoud mag niet langer zijn dan 255 tekens, inclusief de extensie.",
            str(context.exception),
        )

    def test_no_upload_is_unchanged(self):
        form = EnkelvoudigInformatieObjectForm()
        form.cleaned_data = {"inhoud": None}

        self.assertIsNone(form.clean_inhoud())

    def test_model_validation_shortens_uploaded_filename(self):
        document = EnkelvoudigInformatieObject(
            inhoud=SimpleUploadedFile(f"{'a' * 251}.pdf", b"document")
        )

        document.clean_fields(
            exclude=[
                field.name for field in document._meta.fields if field.name != "inhoud"
            ]
        )

        self.assertEqual(document.inhoud.name, f"{'a' * 243}.pdf")

    def test_api_field_uses_model_validator(self):
        from openzaak.components.documenten.api.serializers import (
            EnkelvoudigInformatieObjectSerializer,
        )

        field = EnkelvoudigInformatieObjectSerializer().fields["inhoud"]
        upload = SimpleUploadedFile(f"{'a' * 251}.pdf", b"document")
        field.run_validators(upload)
        self.assertEqual(upload.name, f"{'a' * 243}.pdf")

        upload._name = "a" * 256
        from rest_framework.exceptions import ValidationError as APIValidationError

        with self.assertRaises(APIValidationError):
            field.run_validators(upload)

    def test_stored_filename_is_unchanged(self):
        filename = f"uploads/2026/10/{'a' * 251}.pdf"
        document = EnkelvoudigInformatieObject(inhoud=filename)

        document.clean_fields(
            exclude=[
                field.name for field in document._meta.fields if field.name != "inhoud"
            ]
        )

        self.assertEqual(document.inhoud.name, filename)
