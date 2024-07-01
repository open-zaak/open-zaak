# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from requests_mock import Mocker
from zgw_consumers.test import mock_service_oas_get


def _get_base_url() -> str:
    from notifications_api_common.models import NotificationsConfig

    config = NotificationsConfig.get_solo()
    service = config.notifications_api_service
    assert service is not None, (
        "Use NotificationsConfigMixin in your test case to "
        "properly configure the notications API."
    )
    base_url = service.api_root
    if not base_url.endswith("/"):
        base_url = f"{base_url}/"
    return base_url


def mock_nrc_oas_get(m: Mocker):
    base_url = _get_base_url()
    mock_service_oas_get(m, url=base_url, service="nrc")


def mock_notification_send(m: Mocker, **kwargs) -> None:
    base_url = _get_base_url()
    mock_kwargs = (
        {
            "status_code": 201,
            "json": {"dummy": "json"},
            **kwargs,
        }
        if "exc" not in kwargs
        else kwargs
    )
    m.post(f"{base_url}notificaties", **mock_kwargs)
