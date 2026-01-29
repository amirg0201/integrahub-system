import asyncio
import aio_pika
import json
import os
import requests # Librería para hablar con Slack

# URL por defecto (cámbiala por la tuya o úsala desde docker-compose)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

def enviar_a_slack(mensaje_texto):
    """Envía un JSON a Slack si existe la URL configurada"""
    if not SLACK_WEBHOOK_URL:
        print(f" [!] Slack URL no configurada. Mensaje: {mensaje_texto}")
        return

    payload = {"text": mensaje_texto}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(" [✔] Enviado a Slack correctamente.")
        else:
            print(f" [x] Error Slack: {response.status_code} - {response.text}")
    except Exception as e:
        print(f" [x] Excepción conectando a Slack: {e}")

async def process_notification(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        event_type = body.get('event_type', 'EventoDesconocido')
        data = body.get('data', {})
        order_id = data.get('order_id', 'N/A')
        
        print(f" [📧] Procesando evento: {event_type}")

        # Construimos el mensaje para Slack
        mensaje_slack = ""
        if event_type == "OrderCreated":
            mensaje_slack = f"📦 *Nuevo Pedido Recibido*\nID: `{order_id}`\nEstado: Procesando..."
        elif event_type == "InventoryReserved":
            mensaje_slack = f"✅ *Stock Reservado*\nEl pedido `{order_id}` tiene inventario asegurado."
        
        # Enviar (esto ocurre en segundo plano)
        if mensaje_slack:
            # Usamos run_in_executor para no bloquear el loop asíncrono con requests
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, enviar_a_slack, mensaje_slack)

async def main():
    # Configuración de conexión RabbitMQ
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange("integrahub.events", aio_pika.ExchangeType.TOPIC)
    
    # Cola exclusiva para notificaciones
    queue = await channel.declare_queue("q_notifications", durable=True)

    # Nos suscribimos a todo lo que pase con pedidos (Created, Reserved, etc.)
    await queue.bind(exchange, routing_key="order.#")

    print(f" [*] Notification Worker conectado. Esperando eventos para enviar a Slack...")
    await queue.consume(process_notification)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())