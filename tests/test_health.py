import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api-gateway"))

from fastapi.testclient import TestClient
from main import app


def test_health_endpoint_smoke():
    client = TestClient(app)
    resp = client.get('/health/')
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"api", "rabbitmq", "workers"}
    assert body['api'] == 'ok'
