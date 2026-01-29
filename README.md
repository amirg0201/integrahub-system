# IntegraHub — Proyecto Integrador (resumen)

Este repositorio contiene la solución IntegraHub (demo) — orquestación Order-to-Cash orientada a eventos.

Quickstart
- Local dev:
  python -m venv .venv && source .venv/bin/activate
  pip install -r api-gateway/requirements.txt
  DEV_AUTH_BYPASS=1 uvicorn api-gateway.main:app --reload --port 8000
- Docker (recommended for demo):
  docker compose up --build

Acceptance checklist (para la defensa)
- docker compose up --build -d  ✅
- Demo Portal operativo en http://localhost:8000/ ✅
- RabbitMQ Management visible en http://localhost:15672/ (user/password: see .env.example) ✅
- `/health` expone estado de los componentes ✅
- DLQ + retry visible en RabbitMQ (queues: `order.processing`, `order.processing.retry`, `order.processing.dlq`) ✅

Running tests
- pytest

Files of interest
- `api-gateway/` — FastAPI gateway (serves frontend)
- `workers/inventory-service/` — inventory consumer (DLQ, idempotency)
- `frontend-portal/` — Demo Portal (browser UI)

If you want, I can now open PRs for each P0 item (tests, DLQ, health, CI, docs).
