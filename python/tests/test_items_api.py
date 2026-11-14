from fastapi.testclient import TestClient


def test_create_item(client: TestClient, item_payload: dict[str, object]) -> None:
    response = client.post("/items", json=item_payload)

    assert response.status_code == 201
    assert response.json() == {"id": 1, **item_payload}


def test_create_item_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post("/items", json={"name": "", "price": -1})

    assert response.status_code == 422


def test_list_items_is_empty_initially(client: TestClient) -> None:
    response = client.get("/items")

    assert response.status_code == 200
    assert response.json() == []


def test_list_items_returns_created_items(
    client: TestClient, item_payload: dict[str, object]
) -> None:
    client.post("/items", json=item_payload)
    client.post("/items", json={**item_payload, "name": "Gadget"})

    response = client.get("/items")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [1, 2]


def test_get_item(client: TestClient, item_payload: dict[str, object]) -> None:
    created = client.post("/items", json=item_payload).json()

    response = client.get(f"/items/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_item_missing(client: TestClient) -> None:
    response = client.get("/items/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_replace_item(client: TestClient, item_payload: dict[str, object]) -> None:
    created = client.post("/items", json=item_payload).json()
    updated: dict[str, object] = {
        **item_payload,
        "name": "Renamed",
        "in_stock": False,
    }

    response = client.put(f"/items/{created['id']}", json=updated)

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], **updated}


def test_replace_item_missing(
    client: TestClient, item_payload: dict[str, object]
) -> None:
    response = client.put("/items/999", json=item_payload)

    assert response.status_code == 404


def test_delete_item(client: TestClient, item_payload: dict[str, object]) -> None:
    created = client.post("/items", json=item_payload).json()

    response = client.delete(f"/items/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/items/{created['id']}").status_code == 404


def test_delete_item_missing(client: TestClient) -> None:
    response = client.delete("/items/999")

    assert response.status_code == 404
