# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from openzaak.components.catalogi.tests.test_handle_auth_notifications import (
    HandleAuthNotifTestCase as _HandleAuthNotifTestCase,
)


class HandleAuthNotifTestCase(_HandleAuthNotifTestCase):
    NAMESPACE = "zaken"
