import pytest


@pytest.fixture
def benchmark_assertions(benchmark):
    def wrapper(**kwargs):
        stats = benchmark.stats["stats"]
        for name, value in kwargs.items():
            assert getattr(stats, name) < value, (
                f"{name} {getattr(stats, name)}s exceeded {value}s"
            )

    return wrapper
