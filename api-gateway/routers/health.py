from fastapi import APIRouter
import asyncio
import os
import aio_pika

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health():
    status = {"api": "ok", "rabbitmq": "unknown", "workers": "unknown"}

    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"

    try:
        # quick check with small timeout
        conn = await asyncio.wait_for(aio_pika.connect_robust(connection_url), timeout=3)
        await conn.close()
        status['rabbitmq'] = 'ok'
    except Exception:
        status['rabbitmq'] = 'down'

    # Workers: we can't reliably probe them here; show 'ok' if rabbit is ok
    status['workers'] = 'ok' if status['rabbitmq'] == 'ok' else 'down'

    return status
