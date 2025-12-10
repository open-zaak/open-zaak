import pytest
import requests
from conftest import HEADERS, HEADERS_NON_SUPERUSER, HEADERS_NON_SUPERUSER_MANY_TYPES
from furl import furl

BASE_URL = furl("http://localhost:8000/zaken/api/v1/")


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_zaken_list(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 34}

    def make_request():
        return requests.get((BASE_URL / "zaken").set(params), headers=HEADERS)

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3500
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_zaken_list_non_superuser_few_authorized_types(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 5}

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


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_zaken_list_non_superuser_many_authorized_types(
    benchmark, benchmark_assertions
):
    params = {"pageSize": 100, "page": 29}

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
