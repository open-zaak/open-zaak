import time

import jwt
import pytest
import requests
from furl import furl

BASE_URL = furl("http://localhost:8000/zaken/api/v1/")


BSN_100_ZAKEN = "000000000"
BSN_1000_ZAKEN = "111222333"


def generate_token(client_id: str, secret: str) -> str:
    payload = {
        "iss": "openzaak",
        "iat": int(time.time()),
        "client_id": client_id,
        "user_id": client_id,
        "user_representation": client_id,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


TOKEN_SUPERUSER = generate_token("superuser", "superuser")
HEADERS = {"Authorization": f"Bearer {TOKEN_SUPERUSER}", "Accept-Crs": "EPSG:4326"}


TOKEN_NON_SUPERUSER = generate_token("non_superuser", "non_superuser")
HEADERS_NON_SUPERUSER = {
    "Authorization": f"Bearer {TOKEN_NON_SUPERUSER}",
    "Accept-Crs": "EPSG:4326",
}


TOKEN_NON_SUPERUSER_MANY_TYPES = generate_token(
    "non_superuser_many_types", "non_superuser_many_types"
)
HEADERS_NON_SUPERUSER_MANY_TYPES = {
    "Authorization": f"Bearer {TOKEN_NON_SUPERUSER_MANY_TYPES}",
    "Accept-Crs": "EPSG:4326",
}


@pytest.mark.benchmark(max_time=30, min_rounds=5)
def test_superuser(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 34}

    def make_request():
        return requests.get((BASE_URL / "zaken").set(params), headers=HEADERS)

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3500
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=30, min_rounds=5)
def test_non_superuser_few_authorized_types_1000_zaken(benchmark, benchmark_assertions):
    params = {
        "pageSize": 100,
        "page": 5,
        "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": BSN_1000_ZAKEN,
    }

    def make_request():
        return requests.get(
            (BASE_URL / "zaken").set(params), headers=HEADERS_NON_SUPERUSER
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 525
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=30, min_rounds=5)
def test_non_superuser_many_authorized_types_1000_zaken(
    benchmark, benchmark_assertions
):
    params = {
        "pageSize": 100,
        "page": 5,
        "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": BSN_1000_ZAKEN,
    }

    def make_request():
        return requests.get(
            (BASE_URL / "zaken").set(params), headers=HEADERS_NON_SUPERUSER_MANY_TYPES
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3300
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=30, min_rounds=5)
def test_non_superuser_few_authorized_types_100_zaken(benchmark, benchmark_assertions):
    params = {
        "pageSize": 100,
        "page": 5,
        "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": BSN_100_ZAKEN,
    }

    def make_request():
        return requests.get(
            (BASE_URL / "zaken").set(params), headers=HEADERS_NON_SUPERUSER
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 525
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=30, min_rounds=5)
def test_non_superuser_many_authorized_types_100_zaken(benchmark, benchmark_assertions):
    params = {
        "pageSize": 100,
        "page": 5,
        "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": BSN_100_ZAKEN,
    }

    def make_request():
        return requests.get(
            (BASE_URL / "zaken").set(params), headers=HEADERS_NON_SUPERUSER_MANY_TYPES
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3300
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)
