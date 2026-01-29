import os
import aio_pika
import json

# CAMBIO CLAVE: En Docker, el host es 'rabbitmq' (nombre del servicio).
# En local, usamos 'localhost'.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "password")

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"

async def publish_event(event: dict, routing_key: str):
    # connect_robust ayuda a reconectar si Rabbit se cae momentáneamente
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        # Declaramos el exchange aquí también por seguridad (Idempotencia)
        exchange = await channel.declare_exchange(
            "integrahub.events",
            aio_pika.ExchangeType.TOPIC
        )

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                content_type="application/json"
            ),
            routing_key=routing_key
        )