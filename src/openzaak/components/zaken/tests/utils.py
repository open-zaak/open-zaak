from datetime import datetime

from django.conf import settings
from django.utils import timezone

from vng_api_common.tests import get_operation_url as _get_operation_url

ZAAK_READ_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326"}

ZAAK_WRITE_KWARGS = {"HTTP_ACCEPT_CRS": "EPSG:4326", "HTTP_CONTENT_CRS": "EPSG:4326"}


def utcdatetime(*args, **kwargs) -> datetime:
    return datetime(*args, **kwargs).replace(tzinfo=timezone.utc)


def isodatetime(*args, **kwargs) -> str:
    dt = utcdatetime(*args, **kwargs)
    return dt.isoformat()


def get_operation_url(operation, **kwargs):
    return _get_operation_url(operation, spec_path=settings.SPEC_URL["zaken"], **kwargs)
