import asyncio
import aio_pika
import json
import os
import psycopg2
import time
import random

# Configuración DB
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "secretpassword")
DB_NAME = "integrahub"

# Variable global para el exchange (para poder publicar desde la función)
EXCHANGE_OBJ = None

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(50) NOT NULL,
                customer_id VARCHAR(50),
                status VARCHAR(20),
                amount DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(" [v] Base de datos SQL inicializada.")
    except Exception as e:
        print(f" [!] Esperando a Postgres... ({e})")

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        data = body.get('data', {})
        order_id = data.get('order_id')
        customer_id = data.get('customer_id')
        
        print(f" [1/3] 📦 Procesando inventario para: {order_id}")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 1. RESERVAR
            cur.execute(
                "INSERT INTO orders (order_id, customer_id, status, amount) VALUES (%s, %s, %s, %s)",
                (order_id, customer_id, 'RESERVED', random.uniform(100, 500))
            )
            conn.commit()
            print(f"       ✅ Inventario Reservado.")

            # 2. SIMULAR PAGO
            print(f" [2/3] 💳 Procesando pago...")
            await asyncio.sleep(5) # Usamos await para no bloquear el worker
            
            # 3. CONFIRMAR
            cur.execute(
                "UPDATE orders SET status = 'CONFIRMED', updated_at = NOW() WHERE order_id = %s",
                (order_id,)
            )
            conn.commit()
            cur.close()
            conn.close()
            print(f" [3/3] 🏁 Pedido CONFIRMADO.")

            # --- NUEVO: PUBLICAR EVENTO DE CONFIRMACIÓN (Pub/Sub) ---
            if EXCHANGE_OBJ:
                event_confirmation = {
                    "event_type": "OrderConfirmed",
                    "data": { "order_id": order_id, "status": "CONFIRMED", "customer_id": customer_id }
                }
                await EXCHANGE_OBJ.publish(
                    aio_pika.Message(body=json.dumps(event_confirmation).encode()),
                    routing_key="order.confirmed" # <--- Nueva routing key
                )
                print(f"       📣 Evento 'OrderConfirmed' publicado a RabbitMQ.")

        except Exception as e:
            print(f" [!] Error: {e}")

async def main():
    global EXCHANGE_OBJ
    
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    time.sleep(5)
    init_db()

    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    # 1. Declarar el Exchange de "Muertos" (DLX)
    dlx_exchange = await channel.declare_exchange(
        "dlx.events", aio_pika.ExchangeType.DIRECT
    )

    # 2. Declarar la Cola de "Muertos" (DLQ)
    dlq_queue = await channel.declare_queue("q_inventory_dlq", durable=True)
    await dlq_queue.bind(dlx_exchange, routing_key="dead.inventory")

    # 3. Declarar la Cola Principal CON CONFIGURACIÓN DLQ
    # Aquí está la magia: arguments conecta la cola normal con la DLQ
    args = {
        "x-dead-letter-exchange": "dlx.events",
        "x-dead-letter-routing-key": "dead.inventory"
    }
    
    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )

    # Pasamos 'arguments=args' aquí
    queue = await channel.declare_queue("q_inventory", durable=True, arguments=args)
    await queue.bind(exchange, routing_key="order.created")

    print(' [*] Inventory Worker listo (con DLQ activa). Esperando pedidos...')
    await queue.consume(process_order)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())