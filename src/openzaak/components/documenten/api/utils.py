from django.conf import settings
from django.contrib.sites.models import Site

from rest_framework.reverse import reverse


def get_absolute_url(url_name: str, uuid: str) -> str:
    path = reverse(
        url_name,
        kwargs={"version": settings.REST_FRAMEWORK["DEFAULT_VERSION"], "uuid": uuid},
    )
    domain = Site.objects.get_current().domain
    protocol = "https" if settings.IS_HTTPS else "http"
    return f"{protocol}://{domain}{path}"
