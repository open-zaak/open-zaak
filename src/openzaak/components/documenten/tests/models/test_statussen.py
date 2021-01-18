# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Tests for the business logic w/r to statussen, from RGBZ.
"""
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from ...constants import Statussen
from ..factories import EnkelvoudigInformatieObjectFactory


class StatusTests(TestCase):
    def test_empty_status_empty_ontvangstdatum(self):
        try:
            eio = EnkelvoudigInformatieObjectFactory.create(
                ontvangstdatum=None, status=""
            )
            # The request parameter in the EnkelvoudigInformatieObjectFactory.create() makes the domain name
            # 'testserver', which doesn't match the regex of the URLValidator.
            eio._informatieobjecttype_url = eio._informatieobjecttype_url.replace(
                "testserver", "example.com"
            )
            eio.full_clean()
        except ValidationError:
            self.fail("Empty status and ontvangstdatum should be possible")

    def test_empty_status_non_empty_ontvangstdatum(self):
        try:
            eio = EnkelvoudigInformatieObjectFactory.create(
                ontvangstdatum=date(2018, 12, 24), status=""
            )
            # The request parameter in the EnkelvoudigInformatieObjectFactory.create() makes the domain name
            # 'testserver', which doesn't match the regex of the URLValidator.
            eio._informatieobjecttype_url = eio._informatieobjecttype_url.replace(
                "testserver", "example.com"
            )
            eio.full_clean()
        except ValidationError:
            self.fail("Empty status and non-empty ontvangstdatum should be possible")

    def test_ontvangstdatum_invalid_status(self):
        for invalid_status in Statussen.invalid_for_received():
            with self.subTest(status=invalid_status):
                eio = EnkelvoudigInformatieObjectFactory.create(
                    ontvangstdatum=date(2018, 12, 24), status=invalid_status
                )
                # The request parameter in the EnkelvoudigInformatieObjectFactory.create() makes the domain name
                # 'testserver', which doesn't match the regex of the URLValidator.
                eio._informatieobjecttype_url = eio._informatieobjecttype_url.replace(
                    "testserver", "example.com"
                )
                with self.assertRaises(ValidationError) as exc_context:
                    eio.full_clean()

                code = exc_context.exception.error_dict["status"][0].code
                self.assertEqual(code, "invalid_for_received")
