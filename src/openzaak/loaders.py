import requests
from django_loose_fk.loaders import BaseLoader, FetchError


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects with Authorization header.
    """

    @staticmethod
    def fetch_object(url: str) -> dict:
        from vng_api_common.models import APICredential

        client_auth = APICredential.get_auth(url)
        headers = client_auth.credentials() if client_auth else {}
        response = requests.get(url, headers=headers)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise FetchError(exc.args[0]) from exc
        return response.json()
