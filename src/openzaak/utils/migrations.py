from urllib.parse import urlsplit, urlunsplit

from django.db.models.functions import Length


def get_service(model, url: str):
    """
    copy-paste from zgw_consumers.Service.get_service method, which can't be used
    during migrations
    """
    split_url = urlsplit(url)
    scheme_and_domain = urlunsplit(split_url[:2] + ("", "", ""))

    candidates = (
        model.objects.filter(api_root__startswith=scheme_and_domain)
        .annotate(api_root_length=Length("api_root"))
        .order_by("-api_root_length")
    )

    # select the one matching
    for candidate in candidates.iterator():
        if url.startswith(candidate.api_root):
            return candidate

    return None


def fill_service_urls(
    apps, model, url_field: str, service_base_field: str, service_relative_field: str
):
    """
    helper function to migrate from UrlField to ServiceUrlField
    """
    Service = apps.get_model("zgw_consumers", "Service")
    cache_get_service = {}

    for instance in model.objects.exclude(**{url_field: ""}):
        url = getattr(instance, url_field)

        if url in cache_get_service:
            service = cache_get_service[url]
        else:
            service = get_service(Service, url)
            cache_get_service[url] = service

        relative_url = url[len(service.api_root) :]

        setattr(instance, service_base_field, service)
        setattr(instance, service_relative_field, relative_url)
        instance.save()
