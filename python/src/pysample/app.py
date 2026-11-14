from itertools import count

from fastapi import FastAPI, HTTPException, status

from pysample.models import Item, ItemCreate

app = FastAPI(
    title="pysample",
    description="A sample FastAPI application.",
    version="0.1.0",
)

_items: dict[int, Item] = {}
_id_sequence = count(1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items", response_model=list[Item])
def list_items() -> list[Item]:
    return list(_items.values())


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate) -> Item:
    item = Item(id=next(_id_sequence), **payload.model_dump())
    _items[item.id] = item
    return item


@app.put("/items/{item_id}", response_model=Item)
def replace_item(item_id: int, payload: ItemCreate) -> Item:
    if item_id not in _items:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")
    item = Item(id=item_id, **payload.model_dump())
    _items[item_id] = item
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int) -> None:
    if _items.pop(item_id, None) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")
