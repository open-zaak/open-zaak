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
