# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import http
from django.apps import apps
from django.template import TemplateDoesNotExist, loader
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME

import requests
from vng_api_common.views import ViewConfigView as _ViewConfigView, _test_sites_config
from zds_client import ClientError


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    500 error handler.

    Templates: :template:`500.html`
    Context: None
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        if template_name != ERROR_500_TEMPLATE_NAME:
            # Reraise if it's a missing custom template.
            raise
        return http.HttpResponseServerError(
            "<h1>Server Error (500)</h1>", content_type="text/html"
        )
    context = {"request": request}
    return http.HttpResponseServerError(template.render(context))


class ViewConfigView(_ViewConfigView):
    def get_context_data(self, **kwargs):
        context = {}

        config = []
        config += _test_sites_config(self.request)
        config += _test_nrc_config()

        context["config"] = config
        return context


def _test_nrc_config() -> list:
    if not apps.is_installed("vng_api_common.notifications"):
        return []

    from vng_api_common.notifications.models import NotificationsConfig

    nrc_config = NotificationsConfig.get_solo()

    nrc_client = NotificationsConfig.get_client()

    has_nrc_auth = nrc_client.auth is not None

    checks = [
        (_("NRC"), nrc_config.api_root, nrc_config.api_root.endswith("/")),
        (
            _("Credentials for NRC"),
            _("Configured") if has_nrc_auth else _("Missing"),
            has_nrc_auth,
        ),
    ]

    # check if permissions in AC are fine
    if has_nrc_auth:
        error = False

        try:
            nrc_client.list("kanaal")
        except requests.ConnectionError:
            error = True
            message = _("Could not connect with NRC")
        except ClientError as exc:
            error = True
            message = _(
                "Cannot retrieve kanalen: HTTP {status_code} - {error_code}"
            ).format(status_code=exc.args[0]["status"], error_code=exc.args[0]["code"])
        else:
            message = _("Can retrieve kanalen")

        checks.append((_("NRC connection and authorizations"), message, not error))

    return checks
