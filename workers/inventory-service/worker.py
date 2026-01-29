import asyncio
import os
import json
import sqlite3
from contextlib import closing

import aio_pika

DB_PATH = os.getenv("INVENTORY_DB", "/data/processed.db")

# retry / DLQ policy
RETRY_QUEUE = "order.processing.retry"
MAIN_QUEUE = "order.processing"
DLQ_QUEUE = "order.processing.dlq"
RETRY_DELAY_MS = int(os.getenv("RMQ_RETRY_DELAY_MS", "5000"))
MAX_RETRIES = int(os.getenv("RMQ_MAX_RETRIES", "3"))


def ensure_db():
    # Simple sqlite to record processed correlation_ids (idempotency)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS processed (
                   correlation_id TEXT PRIMARY KEY,
                   processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        conn.commit()


def already_processed(correlation_id: str) -> bool:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute("SELECT 1 FROM processed WHERE correlation_id = ?", (correlation_id,))
        return cur.fetchone() is not None


def mark_processed(correlation_id: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("INSERT OR IGNORE INTO processed(correlation_id) VALUES(?)", (correlation_id,))
        conn.commit()


async def process_order(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        body = json.loads(message.body)
        cid = body.get("correlation_id")
        print(f" [x] Recibido Evento: {body.get('event_type')}  cid={cid}")

        # Idempotency: skip if already processed
        if cid and already_processed(cid):
            print(f" [i] Evento {cid} ya procesado — descartando (idempotency)")
            return

        try:
            print(f"     Procesando inventario para Order ID: {body['data'].get('order_id')}...")

            # Simulación de validación de stock (puede lanzar excepción)
            await asyncio.sleep(1)

            # Aquí validarías stock real; para demo lanzamos excepción si se pide product_id 'FAIL-INV'
            items = body['data'].get('items', [])
            if any(i.get('product_id') == 'FAIL-INV' for i in items):
                raise RuntimeError("Inventario insuficiente (simulado)")

            # Marca como procesado (idempotency)
            if cid:
                mark_processed(cid)

            print(" [v] Inventario Reservado con Éxito.")

        except Exception as exc:
            # Retry pattern: if retries < MAX_RETRIES, publish to retry queue with header; otherwise push to DLQ
            headers = message.headers or {}
            retries = int(headers.get("x-retries", 0))

            if retries < MAX_RETRIES:
                print(f" [!] Procesamiento falló (intent {retries+1}) → reenviando a retry-queue")
                # publish to retry queue with incremented retries and TTL
                channel = message.channel
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.body,
                        headers={**headers, "x-retries": retries + 1},
                        content_type=message.content_type,
                    ),
                    routing_key=RETRY_QUEUE,
                )
                return

            # exceed retries → send to DLQ for manual inspection
            print(" [!] Max retries alcanzado → enviando a DLQ")
            channel = message.channel
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers={**headers, "x-retries": retries},
                    content_type=message.content_type,
                ),
                routing_key=f"{DLQ_QUEUE}",
            )
            return


async def declare_queues(channel: aio_pika.Channel):
    # Exchange used by the system
    exchange = await channel.declare_exchange("integrahub.events", aio_pika.ExchangeType.TOPIC)

    # DLX exchange
    dlx = await channel.declare_exchange("integrahub.dlx", aio_pika.ExchangeType.DIRECT)

    # Main processing queue - messages routed from integrahub.events (routing key: order.created)
    await channel.declare_queue(
        MAIN_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "integrahub.dlx",
            "x-dead-letter-routing-key": f"{DLQ_QUEUE}",
        },
    )
    await channel.bind_queue(MAIN_QUEUE, exchange, routing_key="order.created")

    # Retry queue with TTL — after TTL messages are routed back to the main exchange
    await channel.declare_queue(
        RETRY_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "integrahub.events",
            "x-dead-letter-routing-key": "order.created",
            "x-message-ttl": int(RETRY_DELAY_MS),
        },
    )

    # DLQ (bound to dlx)
    await channel.declare_queue(DLQ_QUEUE, durable=True)
    await channel.bind_queue(DLQ_QUEUE, dlx, routing_key=f"{DLQ_QUEUE}")


async def main():
    ensure_db()

    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")

    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"

    print(f" [*] Conectando a RabbitMQ en: {rmq_host}...")

    connection = await aio_pika.connect_robust(connection_url)
    async with connection:
        channel = await connection.channel()
        await declare_queues(channel)

        queue = await channel.get_queue(MAIN_QUEUE)
        await queue.consume(process_order)

        # Mantener corriendo
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
