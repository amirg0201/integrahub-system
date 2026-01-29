import asyncio
import aio_pika
import json
import os
import psycopg2
import time

# Configuración de Conexión (Lee las variables de Docker)
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "secretpassword")
DB_NAME = "integrahub"

def get_db_connection():
    """Intenta conectar a la base de datos con reintentos"""
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )

def init_db():
    """Crea la tabla si no existe (Migración automática)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(50) NOT NULL,
                customer_id VARCHAR(50),
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(" [v] Base de datos SQL inicializada correctamente.")
    except Exception as e:
        print(f" [!] Esperando a Postgres... ({e})")

async def process_order(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        data = body.get('data', {})
        order_id = data.get('order_id')
        customer_id = data.get('customer_id')
        
        print(f" [x] Procesando pedido: {order_id}")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Insertar en SQL
            cur.execute(
                "INSERT INTO orders (order_id, customer_id, status) VALUES (%s, %s, %s)",
                (order_id, customer_id, 'RESERVED')
            )
            conn.commit()
            cur.close()
            conn.close()
            print(f" [v] Guardado en PostgreSQL exitosamente.")
        except Exception as e:
            print(f" [!] Error guardando en SQL: {e}")

async def main():
    # Variables RabbitMQ
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    # Inicializar Tabla SQL antes de arrancar
    # Damos unos segundos para asegurar que Postgres esté listo
    time.sleep(5) 
    init_db()

    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        "integrahub.events", aio_pika.ExchangeType.TOPIC
    )
    
    queue = await channel.declare_queue("q_inventory", durable=True)
    await queue.bind(exchange, routing_key="order.created")

    print(' [*] Inventory Worker conectado a PostgreSQL. Esperando pedidos...')
    await queue.consume(process_order)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())