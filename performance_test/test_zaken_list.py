import time

import jwt
import pytest
import requests
from furl import furl

BASE_URL = furl("http://localhost:8000/zaken/api/v1/")

payload = {
    # standard claims
    "iss": "foo",
    "iat": int(time.time()),
    # custom claims
    "client_id": "foo",
    "user_id": "foo",
    "user_representation": "foo",
}
TOKEN = jwt.encode(payload, "bar", algorithm="HS256")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept-Crs": "EPSG:4326"}


@pytest.mark.benchmark(max_time=60, min_rounds=5)
def test_objects_api_list(benchmark, benchmark_assertions):
    """
    Regression test for maykinmedia/objects-api#538
    """
    params = {
        "pageSize": 1000,
    }

    def make_request():
        return requests.get((BASE_URL / "zaken").set(params), headers=HEADERS)

    result = benchmark(make_request)

    assert result.status_code == 200
    assert result.json()["count"] == 1000

    benchmark_assertions(mean=1, max=1)
