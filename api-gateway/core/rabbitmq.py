import aio_pika
import json

RABBITMQ_URL = "amqp://user:password@localhost/"

async def publish_event(event: dict, routing_key: str):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "integrahub.events",
        aio_pika.ExchangeType.TOPIC
    )

    await exchange.publish(
        aio_pika.Message(body=json.dumps(event).encode()),
        routing_key=routing_key
    )

    await connection.close()
