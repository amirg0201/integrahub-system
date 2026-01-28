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
    # Conexión
    connection = await aio_pika.connect_robust("amqp://user:password@localhost/")
    channel = await connection.channel()

    # Declarar Exchange y Cola
    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )
    queue = await channel.declare_queue("q_inventory", durable=True)

    # Binding (Enrutamiento [cite: 45])
    await queue.bind(exchange, routing_key="order.created")

    print(' [*] Esperando eventos "order.created". Para salir presiona CTRL+C')

    # Consumir
    await queue.consume(process_order)

    # Mantener corriendo
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
