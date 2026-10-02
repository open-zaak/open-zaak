# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from django_loose_fk.loaders import FetchError, FetchJsonError

from openzaak.loaders import AuthorizedRequestsLoader


class ExternalInformatieObjectTypeUnavailable(Exception):
    def __init__(self, url: str):
        self.url = url
        super().__init__(url)


def get_external_concept(url: str) -> bool:
    try:
        data = AuthorizedRequestsLoader.fetch_object(url, do_underscoreize=False)
    except (FetchError, FetchJsonError) as exc:
        raise ExternalInformatieObjectTypeUnavailable(url) from exc

    if not isinstance(data, dict):
        raise ExternalInformatieObjectTypeUnavailable(url)

    return bool(data.get("concept", False))
