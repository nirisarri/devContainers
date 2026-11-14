import pytest
from pydantic import ValidationError

from pysample.models import Item, ItemCreate


def test_defaults_are_applied() -> None:
    item = ItemCreate(name="Widget", price=1.0)

    assert item.description is None
    assert item.in_stock is True


def test_item_inherits_fields() -> None:
    item = Item(id=1, name="Widget", price=1.0)

    assert item.id == 1
    assert item.name == "Widget"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "x" * 101),
        ("description", "x" * 501),
        ("price", -0.01),
    ],
)
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    payload: dict[str, object] = {"name": "Widget", "price": 1.0, field: value}

    with pytest.raises(ValidationError):
        ItemCreate.model_validate(payload)
