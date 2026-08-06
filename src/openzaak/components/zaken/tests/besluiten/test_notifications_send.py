# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_notifications_send import (
    FailedNotificationTests as _FailedNotificationTests,
    SendNotifTestCase as _SendNotifTestCase,
)


class SendNotifTestCase(_SendNotifTestCase):
    NAMESPACE = "zaken"


class FailedNotificationTests(_FailedNotificationTests):
    NAMESPACE = "zaken"
