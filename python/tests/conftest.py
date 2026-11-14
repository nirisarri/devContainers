from collections.abc import Iterator
from importlib import import_module
from itertools import count

import pytest
from fastapi.testclient import TestClient

from pysample.app import app

# `pysample.__init__` shadows the submodule name, so import it explicitly.
app_module = import_module("pysample.app")


@pytest.fixture(autouse=True)
def reset_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear the module-level in-memory store between tests."""
    monkeypatch.setattr(app_module, "_id_sequence", count(1))
    app_module._items.clear()
    yield
    app_module._items.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def item_payload() -> dict[str, object]:
    return {
        "name": "Widget",
        "description": "A useful widget",
        "price": 9.99,
        "in_stock": True,
    }
