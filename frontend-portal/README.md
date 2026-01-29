# Frontend (IntegraHub Demo Portal) — quick start ✅

This single-file demo is served from `frontend-portal/index.html` and talks to the API Gateway at `http://localhost:8000`.

## Run locally (recommended for development)

1. From project root create a venv and install gateway deps:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r api-gateway/requirements.txt

2. Start the API Gateway (it will also serve the frontend):

   cd api-gateway
   uvicorn main:app --reload --host 127.0.0.1 --port 8000

3. Open the UI:

   http://127.0.0.1:8000/

## Run with Docker (one command)

- From project root:

  docker compose up --build

The stack will start RabbitMQ and the API Gateway (which serves the frontend). Gateway will be available on port `8000`.

## How to test the demo UI

- Normal flow: the gateway requires a JWT (the demo `core/security.py` uses a hardcoded secret). Create a quick token for local testing:

  python -c "from jose import jwt; print(jwt.encode({'sub':'test'}, 'super-secret-key', algorithm='HS256'))"

- Paste that token into the `JWT (Bearer)` field in the UI, then create a new order.

### Dev bypass (fast local development) ⚠️

You can run the gateway in *dev bypass* mode so the API accepts requests without a real JWT.

- Local (uvicorn):

  DEV_AUTH_BYPASS=1 uvicorn api-gateway.main:app --reload --host 127.0.0.1 --port 8000

- Docker Compose (convenience): the compose dev configuration includes `DEV_AUTH_BYPASS=1` for the `api-gateway` service.

When enabled, the UI shows a `Modo dev — omitir JWT` checkbox. If checked the client sends an `X-Dev-User` header and the gateway returns a synthetic payload for `sub`.

## Troubleshooting 🔧

- If the UI shows a network error, confirm the gateway is running on port 8000.
- CORS is permissive in dev (allow_origins = "*").

Enjoy — open an issue here if something fails.
