# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from openzaak.components.catalogi.tests.test_notifications_send import (
    InformatieObjectTypeFailedNotificationTests as _InformatieObjectTypeFailedNotificationTests,
)


class InformatieObjectTypeFailedNotificationTests(
    _InformatieObjectTypeFailedNotificationTests
):
    NAMESPACE = "documenten"
