# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import logging

import factory
import factory.fuzzy


class FailedNotificationFactory(factory.django.DjangoModelFactory):
    logger_name = "vng_api_common.notifications.viewsets"
    level = logging.WARNING
    msg = "Failed to send notification"
    status_code = factory.fuzzy.FuzzyChoice([200, 201, 204])
    message = {
        "aanmaakdatum": "2019-01-01T12:00:00Z",
        "actie": "create",
        "hoofdObject": "http://testserver/foo",
        "kanaal": "zaken",
        "kenmerken": {},
        "resource": "zaak",
        "resourceUrl": "http://testserver/foo",
    }

    class Meta:
        model = "notifications_log.FailedNotification"
