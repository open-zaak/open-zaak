import pytest
import requests
from conftest import HEADERS
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
    1: "00000000-0000-4000-8000-000000000001",
    3: "00000000-0000-4000-8000-000000000003",
    5: "00000000-0000-4000-8000-000000000005",
}


@pytest.fixture(scope="module")
def session():
    with requests.Session() as session:
        session.headers.update(HEADERS)
        yield session


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


@pytest.mark.benchmark(max_time=60, min_rounds=5)
@pytest.mark.parametrize("relation_count", ZAAK_INZAGE_UUIDS.keys())
def test_zaak_inzage_retrieve(benchmark, benchmark_assertions, session, relation_count):
    zaak_id = ZAAK_INZAGE_UUIDS[relation_count]
    url = BASE_URL / f"zaak_inzage/{zaak_id}"

    def make_request():
        return session.get(url)

    result = benchmark(make_request)

    assert result.status_code == 200
    data = result.json()
    assert_relationships(data, relation_count)

    benchmark_assertions(mean=1, median=1)
