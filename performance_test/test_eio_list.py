import pytest
import requests
from furl import furl

from .conftest import HEADERS

BASE_URL = furl("http://localhost:8000/documenten/api/v1/")


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_eio_list(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 34}

    def make_request():
        return requests.get(
            (BASE_URL / "enkelvoudiginformatieobjecten").set(params), headers=HEADERS
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3500
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_eio_list_with_ordering(benchmark, benchmark_assertions):
    params = {"pageSize": 100, "page": 34, "ordering": "-auteur"}

    def make_request():
        return requests.get(
            (BASE_URL / "enkelvoudiginformatieobjecten").set(params), headers=HEADERS
        )

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert data["count"] == 3500
    assert len(data["results"]) == 100

    benchmark_assertions(mean=1, median=1)
