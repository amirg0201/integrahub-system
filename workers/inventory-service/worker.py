import asyncio
import aio_pika
import json


async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        print(f" [x] Recibido Evento: {body['event_type']}")
        print(f"     Correlation ID: {body['correlation_id']}")
        print(
            f"     Procesando inventario para Order ID: {body['data']['order_id']}..."
        )

        # SIMULACIÓN DE TRABAJO (Aquí iría la lógica real de DB)
        await asyncio.sleep(2)

        # Aquí validas stock. Si falla, lanzarías excepción para ir a DLQ (Requisito 4.1 [cite: 47])
        print(" [v] Inventario Reservado con Éxito.")


async def main():
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"

    print(f" [*] Conectando a RabbitMQ en: {rmq_host}...")
    
    # Conexión
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    # Consumir
    await queue.consume(process_order)

    # Mantener corriendo
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
