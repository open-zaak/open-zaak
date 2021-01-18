# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import TestCase

from ..utils.monitoring import filter_sensitive_data


class MonitoringUtilsTests(TestCase):
    maxDiff = None

    def test_filter_sensitive_data_request(self):
        event = {
            "level": "error",
            "exception": {},
            "event_id": "1234",
            "timestamp": "2020-08-28T11:42:17.336757Z",
            "breadcrumbs": [],
            "contexts": {},
            "request": {
                "url": "https://openzaak.nl/zaken/api/v1/rollen",
                "method": "POST",
                "data": {
                    "stuff": 1,
                    "betrokkene_identificatie": {
                        "inp_bsn": 1234567890,
                        "inp_a_nummer": 1234,
                        "anp_identificatie": "string",
                    },
                },
            },
        }

        filtered_event = filter_sensitive_data(event, {})

        filtered_data = {
            "inp_bsn": "(filtered)",
            "inp_a_nummer": "(filtered)",
            "anp_identificatie": "(filtered)",
        }

        self.assertEqual(
            filtered_event["request"]["data"]["betrokkene_identificatie"], filtered_data
        )

    def test_filter_sensitive_data_exception(self):
        event = {
            "level": "error",
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {
                                    "vars": {
                                        "group_data": {
                                            "inp_a_nummer": 1234,
                                            "inp_bsn": 4321,
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "stacktrace": {
                            "frames": [
                                {
                                    "vars": {
                                        "group_data": {"anp_identificatie": "string"}
                                    }
                                }
                            ]
                        }
                    },
                ]
            },
            "event_id": "1234",
            "timestamp": "2020-08-28T11:42:17.336757Z",
            "breadcrumbs": [],
            "contexts": {},
            "request": {
                "url": "https://openzaak.nl/zaken/api/v1/rollen",
                "method": "GET",
            },
        }

        filtered_event = filter_sensitive_data(event, {})

        filtered_values = [
            {
                "stacktrace": {
                    "frames": [
                        {
                            "vars": {
                                "group_data": {
                                    "inp_a_nummer": "(filtered)",
                                    "inp_bsn": "(filtered)",
                                }
                            }
                        }
                    ]
                }
            },
            {
                "stacktrace": {
                    "frames": [
                        {"vars": {"group_data": {"anp_identificatie": "(filtered)"}}}
                    ]
                }
            },
        ]

        self.assertEqual(filtered_event["exception"]["values"], filtered_values)

    def test_filter_sensitive_data_querystring(self):
        event = {
            "level": "error",
            "exception": {},
            "event_id": "1234",
            "timestamp": "2020-08-28T11:42:17.336757Z",
            "breadcrumbs": [],
            "contexts": {},
            "request": {
                "url": "https://openzaak.nl/zaken/api/v1/rollen",
                "method": "GET",
                "querystring": (
                    "?somefield=bla&betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=4321"
                    "&betrokkeneIdentificatie__natuurlijkPersoon__anpIdentificatie=identificatie"
                    "&betrokkeneIdentificatie__natuurlijkPersoon__inpA_nummer=1234"
                ),
            },
        }

        filtered_event = filter_sensitive_data(event, {})

        filtered_querystring = (
            "?somefield=bla&betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=(filtered)"
            "&betrokkeneIdentificatie__natuurlijkPersoon__anpIdentificatie=(filtered)"
            "&betrokkeneIdentificatie__natuurlijkPersoon__inpA_nummer=(filtered)"
        )

        self.assertEqual(filtered_event["request"]["querystring"], filtered_querystring)
