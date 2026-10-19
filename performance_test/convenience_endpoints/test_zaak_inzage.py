import pytest
import requests
from conftest import HEADERS, HEADERS_NON_SUPERUSER, HEADERS_NON_SUPERUSER_MANY_TYPES
from furl import furl

BASE_URL = furl("http://localhost:8000/zaken/api/v1/")
ZAAK_COLLECTION_RELATIONSHIPS = (
    "deelzaken",
    "eigenschappen",
    "besluiten",
    "rollen",
    "statussen",
    "zaakcontactmomenten",
    "zaakinformatieobjecten",
    "zaakobjecten",
    "zaakverzoeken",
    "zaaknotities",
)
ZAAKTYPE_COLLECTION_RELATIONSHIPS = (
    "eigenschappen",
    "resultaattypen",
    "roltypen",
    "statustypen",
    "zaakobjecttypen",
    "informatieobjecttypen",
)

ZAAK_INZAGE_UUIDS = {
    1: "00000000-0000-4000-8000-000000000001",  # with non_superuser auth
    3: "00000000-0000-4000-8000-000000000003",  # with non_superuser_many_types auth
    5: "00000000-0000-4000-8000-000000000005",
}


@pytest.mark.benchmark(max_time=60, min_rounds=5)
@pytest.mark.parametrize("relation_count", ZAAK_INZAGE_UUIDS.keys())
def test_zaak_inzage_retrieve(benchmark, benchmark_assertions, relation_count):
    zaak_id = ZAAK_INZAGE_UUIDS[relation_count]
    url = str(BASE_URL / f"zaak-inzage/{zaak_id}")

    def make_request():
        return requests.get(url, headers=HEADERS)

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()

    def assert_relationships(data, relation_count):
        """Assert the relationship of the zaak"""
        assert data["zaaktype"]
        assert data["resultaat"]
        assert data["status"]
        assert data["hoofdzaak"] is None

        for relationship in ZAAK_COLLECTION_RELATIONSHIPS:
            assert len(data[relationship]) == relation_count, relationship

        for relationship in ZAAKTYPE_COLLECTION_RELATIONSHIPS:
            assert len(data["zaaktype"][relationship]) == relation_count, relationship

        for status in data["statussen"]:
            assert len(status["substatussen"]) == relation_count

    assert_relationships(data, relation_count)

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=60, min_rounds=5)
@pytest.mark.parametrize("relation_count", ZAAK_INZAGE_UUIDS.keys())
def test_zaak_inzage_non_superuser_few_authorized_types(
    benchmark, benchmark_assertions, relation_count
):
    zaak_id = ZAAK_INZAGE_UUIDS[relation_count]
    url = str(BASE_URL / f"zaak-inzage/{zaak_id}")

    def make_request():
        return requests.get(url, headers=HEADERS_NON_SUPERUSER)

    result = benchmark(make_request)

    if relation_count == 1:
        assert result.status_code == 200
    else:
        assert result.status_code == 403

    benchmark_assertions(mean=1, median=1)


@pytest.mark.benchmark(max_time=60, min_rounds=5)
@pytest.mark.parametrize("relation_count", ZAAK_INZAGE_UUIDS.keys())
def test_zaak_inzage_non_superuser_many_authorized_types(
    benchmark, benchmark_assertions, relation_count
):
    zaak_id = ZAAK_INZAGE_UUIDS[relation_count]
    url = str(BASE_URL / f"zaak-inzage/{zaak_id}")

    def make_request():
        return requests.get(url, headers=HEADERS_NON_SUPERUSER_MANY_TYPES)

    result = benchmark(make_request)

    if relation_count == 3:
        assert result.status_code == 200
    else:
        assert result.status_code == 403

    benchmark_assertions(mean=1, median=1)
