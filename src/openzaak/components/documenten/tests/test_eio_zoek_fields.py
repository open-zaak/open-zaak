# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from django.test import SimpleTestCase, tag

from drf_spectacular.drainage import get_override
from privates.test import temp_private_root
from rest_framework import serializers, status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from ...catalogi.api.scopes import SCOPE_CATALOGI_READ
from ...catalogi.tests.factories import InformatieObjectTypeFactory
from ..api.scopes import SCOPE_DOCUMENTEN_ALLES_LEZEN
from ..api.serializers import EIOZoekFieldsSerializer
from .factories import EnkelvoudigInformatieObjectFactory


@tag("gh-2635")
class EIOZoekFieldsValidationTests(SimpleTestCase):
    def test_schema_example_is_accepted(self):
        example = get_override(EIOZoekFieldsSerializer(), "field")["example"]
        self.assertEqual(
            example,
            [
                "url",
                "identificatie",
                "titel",
                {"informatieobjecttype": ["omschrijving"]},
            ],
        )

        result = EIOZoekFieldsSerializer().run_validation(example)

        self.assertEqual(
            result,
            {
                "url": None,
                "identificatie": None,
                "titel": None,
                "informatieobjecttype": {"omschrijving": None},
            },
        )

    def test_wildcard_selects_everything(self):
        result = EIOZoekFieldsSerializer().run_validation(["*"])

        self.assertEqual(result, {"*": None})

    def test_plain_field_cannot_be_nested(self):
        with self.assertRaises(serializers.ValidationError) as error:
            EIOZoekFieldsSerializer().run_validation([{"titel": ["x"]}])

        detail = error.exception.detail[0]
        self.assertEqual(detail.code, "not_nested")
        self.assertEqual(str(detail), "Field titel does not support nested selection.")

    def test_unknown_field(self):
        with self.assertRaises(serializers.ValidationError) as error:
            EIOZoekFieldsSerializer().run_validation(["doesNotExist"])

        detail = error.exception.detail[0]
        self.assertEqual(detail.code, "unknown_field")
        self.assertEqual(str(detail), "Unknown response field: doesNotExist.")

    def test_unknown_nested_field_reports_full_path(self):
        with self.assertRaises(serializers.ValidationError) as error:
            EIOZoekFieldsSerializer().run_validation(
                [{"informatieobjecttype": ["nope"]}]
            )

        detail = error.exception.detail[0]
        self.assertEqual(detail.code, "unknown_field")
        self.assertEqual(
            str(detail), "Unknown response field: informatieobjecttype.nope."
        )


@tag("gh-2635")
@temp_private_root()
class EIOZoekFieldsEndpointTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy("enkelvoudiginformatieobject--zoek")

    def search(self, fields, *, query_params=None, **extra):
        return self.client.post(
            self.url, {"fields": fields, **extra}, query_params=query_params
        )

    def test_only_selected_fields_are_returned(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        response = self.search(["url", "titel"], uuid__in=[str(eio.uuid)])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(set(results[0]), {"url", "titel"})
        self.assertEqual(results[0]["titel"], eio.titel)
        self.assertEqual(results[0]["url"], f"http://testserver{reverse(eio)}")

    def test_omitted_fields_and_wildcard_return_complete_response(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        complete = self.client.post(self.url, {"uuid__in": [str(eio.uuid)]})
        selected = self.search(["*"], uuid__in=[str(eio.uuid)])

        self.assertEqual(complete.status_code, status.HTTP_200_OK)
        self.assertEqual(selected.status_code, status.HTTP_200_OK)
        complete_data = complete.json()
        self.assertEqual(selected.json(), complete_data)
        self.assertEqual(len(complete_data["results"]), 1)
        self.assertIn("titel", complete_data["results"][0])
        self.assertIn("informatieobjecttype", complete_data["results"][0])

    def test_empty_selection(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        response = self.search([], uuid__in=[str(eio.uuid)])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"], [{}])

    def test_fields_and_expand_are_mutually_exclusive(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        uuid_in = [str(eio.uuid)]

        for body, query_params in (
            ({"expand": ["informatieobjecttype"]}, {}),
            ({}, {"expand": "informatieobjecttype"}),
            ({}, {"expand": ""}),
        ):
            with self.subTest(body=body, query_params=query_params):
                response = self.search(
                    ["url"], query_params=query_params, uuid__in=uuid_in, **body
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], "invalid")
                error = get_validation_errors(response, "nonFieldErrors")
                self.assertEqual(error["code"], "invalid_field")
                self.assertEqual(
                    error["reason"],
                    "Het gebruik van het `fields` en `expand` element is mutual exclusive.",
                )

    def test_uuid_in_is_still_required(self):
        response = self.search(["url", "titel"])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "uuid__in")
        self.assertEqual(error["code"], "required")

    def test_invalid_field_selections(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        # `error_messages` includes the messages inherited from DRF's `ListField`
        messages = EIOZoekFieldsSerializer().error_messages

        for fields, code, message in (
            ("uuid", "not_a_list", messages["not_a_list"].format(input_type="str")),
            ([True], "invalid_selection", messages["invalid_selection"]),
            (
                ["doesNotExist"],
                "unknown_field",
                messages["unknown_field"].format(name="doesNotExist"),
            ),
            (
                [{"titel": ["url"]}],
                "not_nested",
                messages["not_nested"].format(name="titel"),
            ),
        ):
            with self.subTest(fields=fields):
                response = self.search(fields, uuid__in=[str(eio.uuid)])

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], "invalid")
                error = get_validation_errors(response, "fields")
                self.assertEqual(error["code"], code)
                self.assertEqual(error["reason"], str(message))

    def test_fields_do_not_break_the_uuid_filter(self):
        eio1, eio2, eio3 = EnkelvoudigInformatieObjectFactory.create_batch(3)

        response = self.search(["url"], uuid__in=[str(eio1.uuid), str(eio3.uuid)])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertCountEqual(
            results,
            [
                {"url": f"http://testserver{reverse(eio1)}"},
                {"url": f"http://testserver{reverse(eio3)}"},
            ],
        )


@tag("gh-2635")
@temp_private_root()
class EIOZoekFieldsAuthTests(JWTAuthMixin, APITestCase):
    scopes = [SCOPE_DOCUMENTEN_ALLES_LEZEN]
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.openbaar
    component = ComponentTypes.drc
    url = reverse_lazy("enkelvoudiginformatieobject--zoek")

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        super().setUpTestData()

    def test_selection_does_not_bypass_authorizations(self):
        allowed = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        other_type = EnkelvoudigInformatieObjectFactory.create(
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar
        )
        too_confidential = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )
        uuids = [str(eio.uuid) for eio in (allowed, other_type, too_confidential)]

        response = self.client.post(
            self.url, {"uuid__in": uuids, "fields": ["url", "titel"]}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(
            results,
            [{"url": f"http://testserver{reverse(allowed)}", "titel": allowed.titel}],
        )

    def test_nested_informatieobjecttype_requires_catalogi_read_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        data = {
            "uuid__in": [str(eio.uuid)],
            "fields": [{"informatieobjecttype": ["omschrijving"]}],
        }

        with self.subTest("without catalogi scope"):
            response = self.client.post(self.url, data)

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("with catalogi scope"):
            Autorisatie.objects.create(
                applicatie=self.applicatie,
                component=ComponentTypes.ztc,
                scopes=[SCOPE_CATALOGI_READ],
            )

            response = self.client.post(self.url, data)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["results"],
                [
                    {
                        "_expand": {
                            "informatieobjecttype": {
                                "omschrijving": self.informatieobjecttype.omschrijving
                            }
                        }
                    }
                ],
            )

    def test_plain_relation_url_does_not_require_expansion_scope(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.client.post(
            self.url,
            {"uuid__in": [str(eio.uuid)], "fields": ["informatieobjecttype"]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "informatieobjecttype": self.check_for_instance(
                        self.informatieobjecttype
                    )
                }
            ],
        )

    def test_selection_without_documenten_scope_is_forbidden(self):
        self.autorisatie.delete()

        response = self.client.post(self.url, {"uuid__in": [], "fields": ["url"]})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
