import asyncio
import aio_pika
import json
import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "secretpassword")
DB_NAME = "integrahub"

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

def init_analytics_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Tabla especial para métricas (Dashboard)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_daily (
                date DATE PRIMARY KEY DEFAULT CURRENT_DATE,
                total_orders INT DEFAULT 0,
                total_revenue DECIMAL(15, 2) DEFAULT 0.00,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print(" [📊] Tabla de Analítica lista.")
    except Exception as e:
        print(f" [!] Error DB Analítica: {e}")

async def process_metric(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        event_type = body.get('event_type')
        
        # Solo nos interesa sumar dinero cuando se CONFIRMA
        if event_type == "OrderConfirmed":
            data = body.get('data', {})
            order_id = data.get('order_id')
            
            # Nota: En un sistema real, el evento debería traer el monto.
            # Aquí consultamos el monto de la orden recién guardada para sumar.
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # 1. Obtener monto de la orden
                cur.execute("SELECT amount FROM orders WHERE order_id = %s", (order_id,))
                result = cur.fetchone()
                
                if result:
                    amount = result[0]
                    
                    # 2. Actualizar Métricas del Día (Upsert)
                    cur.execute("""
                        INSERT INTO analytics_daily (date, total_orders, total_revenue, last_updated)
                        VALUES (CURRENT_DATE, 1, %s, NOW())
                        ON CONFLICT (date) DO UPDATE SET
                            total_orders = analytics_daily.total_orders + 1,
                            total_revenue = analytics_daily.total_revenue + %s,
                            last_updated = NOW();
                    """, (amount, amount))
                    
                    conn.commit()
                    print(f" [📈] Métrica Actualizada: +${amount} (Orden {order_id})")
                
                cur.close()
                conn.close()
            except Exception as e:
                print(f" [!] Error actualizando métricas: {e}")

async def main():
    rmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rmq_user = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    rmq_pass = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    
    init_analytics_db()

    connection_url = f"amqp://{rmq_user}:{rmq_pass}@{rmq_host}/"
    connection = await aio_pika.connect_robust(connection_url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange("integrahub.events", aio_pika.ExchangeType.TOPIC)
    queue = await channel.declare_queue("q_analytics", durable=True)
    
    # Escuchamos solo confirmaciones (donde hay dinero)
    await queue.bind(exchange, routing_key="order.confirmed")

    print(' [*] Analytics Worker (Streaming) esperando datos...')
    await queue.consume(process_metric)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())