import asyncio
import aio_pika
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Configuración de Mongo
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        print(f" [x] Recibido Evento: {body.get('event_type')}")
        
        # 1. Conexión a MongoDB
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.integrahub
        collection = db.orders

        order_data = body.get('data', {})
        order_id = order_data.get('order_id')
        
        # 2. Guardar en Base de Datos (Persistencia)
        documento = {
            "order_id": order_id,
            "status": "RESERVED",
            "items": order_data.get('items', []),
            "customer_id": order_data.get('customer_id'),
            "raw_event": body
        }

        try:
            result = await collection.insert_one(documento)
            print(f" [v] Guardado en MongoDB con ID: {result.inserted_id}")
        except Exception as e:
            print(f" [!] Error guardando en Mongo: {e}")

async def main():
    # Variables de entorno
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"

    # Conexión RabbitMQ
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    # Declarar Exchange
    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )

    # --- AQUÍ ESTABA EL ERROR ANTES ---
    # Forma correcta de declarar y "bindear" la cola:
    queue = await channel.declare_queue("q_inventory", durable=True)
    await queue.bind(exchange, routing_key="order.created")
    # ----------------------------------

    print(f' [*] Inventory Worker conectado a Mongo en {MONGO_URI}')
    print(' [*] Esperando eventos...')

    await queue.consume(process_order)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())