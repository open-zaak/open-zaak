# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import TestCase as DjangoTestCase

from django_webtest import (
    TransactionWebTest as DjangoTransactionWebTest,
    WebTest as DjangoWebTest,
)
from maykin_2fa.test import disable_admin_mfa


@disable_admin_mfa()
class WebTest(DjangoWebTest):
    pass


@disable_admin_mfa()
class TransactionWebTest(DjangoTransactionWebTest):
    pass


@disable_admin_mfa()
class TestCase(DjangoTestCase):
    pass
