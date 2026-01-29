import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api-gateway"))

import pytest
from fastapi.testclient import TestClient

from main import app


def async_noop(*a, **k):
    async def _():
        return None
    return _


@pytest.fixture(autouse=True)
def enable_dev_bypass(monkeypatch):
    monkeypatch.setenv('DEV_AUTH_BYPASS', '1')


def test_create_order_happy_path(monkeypatch):
    # mock publish_event to avoid real AMQP calls
    import routers.orders as orders_module

    async def fake_publish(event, rk):
        assert event['event_type'] == 'OrderCreated'
        return True

    monkeypatch.setattr(orders_module, 'publish_event', fake_publish)

    client = TestClient(app)
    resp = client.post('/orders', json={
        'customer_id': 'CUST-1',
        'items': [{'product_id': 'P1', 'quantity': 1}]
    })

    assert resp.status_code == 202
    body = resp.json()
    assert 'order_id' in body and 'correlation_id' in body


def test_create_order_missing_fields():
    client = TestClient(app)
    resp = client.post('/orders', json={'customer_id': 'CUST-1'})
    assert resp.status_code == 422
