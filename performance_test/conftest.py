import time

import jwt
import pytest


@pytest.fixture
def benchmark_assertions(benchmark):
    """Assert hard upper bounds on benchmark metrics.
    e.g. to assert the median duration per round is less than 1s.

    .. code-block::
        def my_bench(benchmark, benchmark_assertions):
            def addition():
                return 1 + 1
            assert benchmark(addition) == 2

            assert benchmark_assertions(median=1)
    """

    def wrapper(**kwargs):
        stats = benchmark.stats["stats"]
        for name, value in kwargs.items():
            assert getattr(stats, name) < value, (
                f"{name} {getattr(stats, name)}s exceeded {value}s"
            )

    return wrapper


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
