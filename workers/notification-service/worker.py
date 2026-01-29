import asyncio
import aio_pika
import json
import os
import aiohttp
import logging
from datetime import datetime, timedelta
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    BeforeSleep
)

# Configuración de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# --- ESTADO DEL CIRCUIT BREAKER ---
# Si falla demasiadas veces, guardamos aquí hasta qué hora debemos dejar de intentar.
circuit_open_until = None
CIRCUIT_BREAKER_TIMEOUT = 30  # Segundos que el circuito se queda abierto tras fallo crítico

# Función auxiliar para logs de tenacity
def log_retry_attempt(retry_state):
    logger.warning(f" [⚠️] Fallo al conectar. Reintentando en {retry_state.next_action.sleep}s... (Intento {retry_state.attempt_number})")

# --- LÓGICA DE ENVÍO CON RESILIENCIA ---
# 2. RETRIES CON BACKOFF: 
# Si falla, reintenta 3 veces. Espera 2s, luego 4s, luego 8s (exponencial).
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    before_sleep=log_retry_attempt,
    reraise=True # Importante: si fallan los 3 intentos, lanza el error para activar el Circuit Breaker
)
async def _execute_slack_request(session, payload):
    # 1. TIMEOUT:
    # Si Slack no responde en 5 segundos, se corta la conexión (evita hilos colgados).
    timeout = aiohttp.ClientTimeout(total=5)
    
    async with session.post(SLACK_WEBHOOK_URL, json=payload, timeout=timeout) as resp:
        if resp.status >= 500:
            # Forzamos error en 500 para que tenacity reintente
            resp.raise_for_status() 
        elif resp.status >= 400:
            logger.error(f" [!] Error Cliente Slack (No reintentable): {resp.status}")
        else:
            logger.info(" [✔] Notificación enviada a Slack exitosamente.")

async def send_to_slack(text):
    global circuit_open_until
    
    # 3. CIRCUIT BREAKER (Mecanismo Equivalente):
    # Antes de intentar, miramos si el circuito está abierto (en enfriamiento).
    if circuit_open_until:
        if datetime.now() < circuit_open_until:
            logger.error(" [🔌] CIRCUIT BREAKER ABIERTO: Omitiendo envío a Slack por protección.")
            return # Salimos sin intentar conectar
        else:
            logger.info(" [🔌] Circuit Breaker: Tiempo de espera finalizado. Cerrando circuito y reanudando envíos.")
            circuit_open_until = None # Reseteamos el circuito

    if not SLACK_WEBHOOK_URL or "http" not in SLACK_WEBHOOK_URL:
        logger.warning(f" [x] Slack URL no configurada, omitiendo: {text}")
        return

    async with aiohttp.ClientSession() as session:
        payload = {"text": text}
        try:
            await _execute_slack_request(session, payload)
        except Exception as e:
            # MANEJO DE FALLOS DEMOSTRABLE:
            # Si tenacity se rinde tras 3 intentos, caemos aquí.
            logger.critical(f" [💥] FALLO CRÍTICO: Slack no responde tras reintentos. Error: {e}")
            
            # ABRIMOS EL CIRCUIT BREAKER
            circuit_open_until = datetime.now() + timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT)
            logger.warning(f" [🔌] ABRIENDO CIRCUIT BREAKER por {CIRCUIT_BREAKER_TIMEOUT} segundos.")

# --- PROCESAMIENTO DE MENSAJES ---

async def process_notification(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        event_type = body.get('event_type')
        data = body.get('data', {})
        order_id = data.get('order_id')
        
        logger.info(f" [📧] Recibido evento: {event_type}")

        slack_message = ""
        
        if event_type == "OrderCreated":
            slack_message = f"📦 *Nuevo Pedido Recibido*\nID: `{order_id}`\nEstado: *Procesando Inventario...*"
            logger.info(f"      [Simulación] ✉️ Enviando email de 'Recibido' al cliente {data.get('customer_id')}...")

        elif event_type == "OrderConfirmed":
            slack_message = f"✅ *Pedido Confirmado*\nID: `{order_id}`\nEstado: *Pago Aprobado y Stock Reservado*"
            logger.info(f"      [Simulación] ✉️ Enviando factura electrónica al cliente {data.get('customer_id')}...")
        
        if slack_message:
            await send_to_slack(slack_message)

async def main():
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    
    # Lógica de reconexión robusta para RabbitMQ (Infraestructura Resiliente)
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )

    queue = await channel.declare_queue("q_notifications", durable=True)
    await queue.bind(exchange, routing_key="order.#")

    logger.info(' [*] Notification Worker (Resilient) esperando eventos...')
    await queue.consume(process_notification)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())