import json

import requests
from django_loose_fk.loaders import BaseLoader, FetchError, FetchJsonError
from djangorestframework_camel_case.util import underscoreize


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects with Authorization header.
    """

    @staticmethod
    def fetch_object(url: str, do_underscoreize=True) -> dict:
        from vng_api_common.models import APICredential

        client_auth = APICredential.get_auth(url)
        headers = client_auth.credentials() if client_auth else {}

        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as exc:
            raise FetchError(exc.args[0]) from exc

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise FetchError(exc.args[0]) from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise FetchJsonError(exc.args[0]) from exc

        if not do_underscoreize:
            return data

        return underscoreize(data)
