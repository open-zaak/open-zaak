#!/usr/bin/env python
import os
import timeit
from concurrent.futures import ThreadPoolExecutor

import requests
from zds_client import ClientAuth


def separate_requests(auth: ClientAuth, reqs):
    headers = {
        **auth.credentials(),
        "Accept-Crs": "EPSG:4326",
    }

    def request(config_dict):
        method, url = config_dict["method"], config_dict["url"]
        response = getattr(requests, method)(url, headers=headers)
        return response.json()

    with ThreadPoolExecutor() as executor:
        responses = executor.map(request, reqs)

    list(responses)


def bulk(auth, url, reqs):
    body = reqs
    headers = {
        **auth.credentials(),
        "Accept-Crs": "EPSG:4326",
    }
    response = requests.post(url, json=body, headers=headers)
    response.json()


if __name__ == "__main__":
    do_bulk = "OZ_BULK" in os.environ
    client_id = os.getenv("OZ_CLIENT_ID")
    secret = os.getenv("OZ_SECRET")
    url = os.getenv("OZ_BATCH_ENDPOINT", "http://localhost:8000/api/v1/batch")
    zaaktype = os.getenv(
        "OZ_ZAAKTYPE",
        "http://localhost:8000/catalogi/api/v1/zaaktypen/4b43a910-db79-4daa-a492-a5312d12d894",
    )
    NUM_ITER = int(os.getenv("OZ_ITERATIONS", "100"))

    reqs = [
        {
            "method": "get",
            "url": f"http://localhost:8000/zaken/api/v1/zaken?zaaktype={zaaktype}",
        },
        {"method": "get", "url": f"http://localhost:8000/besluiten/api/v1/besluiten"},
        {"method": "get", "url": f"http://localhost:8000/documenten/api/v1/"},
        {
            "method": "get",
            "url": f"http://localhost:8000/autorisaties/api/v1/applicaties",
        },
        {
            "method": "get",
            "url": f"http://localhost:8000/zaken/api/v1/zaken/097056c9-a74d-43f6-9c5d-512e8e8cb9d7",
        },
        {"method": "get", "url": f"http://localhost:8000/catalogi/api/v1/zaaktypen"},
    ]

    reqs = reqs * 2

    auth = ClientAuth(client_id, secret)

    if do_bulk:
        main = lambda: bulk(auth, url, reqs)  # noqa
    else:
        main = lambda: separate_requests(auth, reqs)  # noqa

    print(timeit.timeit(main, number=NUM_ITER))
