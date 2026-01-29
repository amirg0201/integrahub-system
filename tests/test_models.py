import pytest
from pathlib import Path
import sys

# ensure api-gateway is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api-gateway"))

from models.orders import OrderRequest, OrderItem


def test_order_item_validation():
    item = OrderItem(product_id="P1", quantity=2)
    assert item.product_id == "P1"


@pytest.mark.parametrize("bad", [
    {},
    {"customer_id": "C1"},
    {"customer_id": "C1", "items": [{}]},
])
def test_order_request_invalid(bad):
    with pytest.raises(Exception):
        OrderRequest(**bad)
