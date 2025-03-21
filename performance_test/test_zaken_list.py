import time

import jwt
import pytest
import requests
from furl import furl

BASE_URL = furl("http://localhost:8000/zaken/api/v1/")


def generate_token(client_id: str, secret: str) -> str:
    payload = {
        "iss": "openzaak",
        "iat": int(time.time()),
        "client_id": client_id,
        "user_id": client_id,
        "user_representation": client_id,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


TOKEN_SUPERUSER = generate_token("foo", "bar")
HEADERS = {"Authorization": f"Bearer {TOKEN_SUPERUSER}", "Accept-Crs": "EPSG:4326"}

TOKEN_NON_SUPERUSER = generate_token("non_superuser", "non_superuser")
HEADERS_NON_SUPERUSER = {
    "Authorization": f"Bearer {TOKEN_NON_SUPERUSER}",
    "Accept-Crs": "EPSG:4326",
}


TOKEN_NON_SUPERUSER = generate_token("non_superuser", "non_superuser")
HEADERS_NON_SUPERUSER = {
    "Authorization": f"Bearer {TOKEN_NON_SUPERUSER}",
    "Accept-Crs": "EPSG:4326",
}


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_zaken_list(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 34}

    def make_request():
        return requests.get((BASE_URL / "zaken").set(params), headers=HEADERS)

    result = benchmark(make_request)

    assert result.status_code == 200
    assert result.json()["count"] == 3500

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_zaken_list_non_superuser(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 29}

    def make_request():
        return requests.get(
            (BASE_URL / "zaken").set(params), headers=HEADERS_NON_SUPERUSER
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    assert result.json()["count"] == 3000

    benchmark_assertions(mean=1, median=1)
