import asyncio
import aio_pika
import json
import os
import aiohttp

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

async def send_to_slack(text):
    if not SLACK_WEBHOOK_URL or "hooks.slack.com" not in SLACK_WEBHOOK_URL:
        print(f" [x] Slack URL no configurada, omitiendo envío: {text}")
        return

    async with aiohttp.ClientSession() as session:
        payload = {"text": text}
        try:
            async with session.post(SLACK_WEBHOOK_URL, json=payload) as resp:
                if resp.status == 200:
                    print(" [✔] Notificación enviada a Slack.")
                else:
                    print(f" [!] Error Slack: {resp.status}")
        except Exception as e:
            print(f" [!] Excepción conectando a Slack: {e}")

async def process_notification(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        event_type = body.get('event_type')
        data = body.get('data', {})
        order_id = data.get('order_id')
        
        print(f" [📧] Recibido evento: {event_type}")

        # Lógica de Notificación según el estado (Flujo B)
        slack_message = ""
        
        if event_type == "OrderCreated":
            slack_message = f"📦 *Nuevo Pedido Recibido*\nID: `{order_id}`\nEstado: *Procesando Inventario...*"
            # Simulación notificación cliente
            print(f"      [Simulación] ✉️ Enviando email de 'Recibido' al cliente {data.get('customer_id')}...")

        elif event_type == "OrderConfirmed":
            slack_message = f"✅ *Pedido Confirmado*\nID: `{order_id}`\nEstado: *Pago Aprobado y Stock Reservado*"
            # Simulación notificación cliente
            print(f"      [Simulación] ✉️ Enviando factura electrónica al cliente {data.get('customer_id')}...")
        
        # Enviar a Slack si hay mensaje
        if slack_message:
            await send_to_slack(slack_message)

async def main():
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )

    queue = await channel.declare_queue("q_notifications", durable=True)
    
    # CAMBIO IMPORTANTE: Usamos "order.#" para escuchar CREADOS y CONFIRMADOS
    await queue.bind(exchange, routing_key="order.#")

    print(' [*] Notification Worker (Slack + Email Sim) esperando eventos...')
    await queue.consume(process_notification)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())