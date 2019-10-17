from django.conf import settings as django_settings


def settings(request):
    public_settings = (
        "GOOGLE_ANALYTICS_ID",
        "ENVIRONMENT",
        "ENVIRONMENT_SHOWN_IN_ADMIN",
        "PROJECT_NAME",
        "SITE_TITLE",
        "API_VERSION",
        "GIT_SHA",
    )

    return {
        "settings": dict(
            [(k, getattr(django_settings, k, None)) for k in public_settings]
        )
    }
