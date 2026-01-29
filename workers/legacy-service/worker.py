import time
import os
import shutil
import pandas as pd
import psycopg2
from datetime import datetime

# Configuración
INBOX_DIR = "/app/inbox"
PROCESSED_DIR = "/app/processed"
ERROR_DIR = "/app/error"

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "secretpassword")
DB_NAME = "integrahub"

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

def process_csv(filepath):
    print(f" [📄] Procesando archivo: {os.path.basename(filepath)}...")
    
    try:
        # 1. Validar formato (Pandas)
        df = pd.read_csv(filepath)
        required_cols = ['order_id', 'customer_id', 'amount']
        
        # Validar columnas
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Faltan columnas requeridas: {required_cols}")

        conn = get_db_connection()
        cur = conn.cursor()

        rows_inserted = 0
        
        # 2. Iterar y Cargar (ETL)
        for index, row in df.iterrows():
            try:
                # Validación de Datos: Monto debe ser positivo
                if row['amount'] <= 0:
                    print(f"      ⚠️ Fila {index}: Monto inválido ({row['amount']}). Saltando.")
                    continue

                # Insertar en DB (Simulando una carga masiva histórica)
                cur.execute(
                    "INSERT INTO orders (order_id, customer_id, status, amount) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (row['order_id'], row['customer_id'], 'IMPORTED', row['amount'])
                )
                rows_inserted += 1
            except Exception as row_error:
                print(f"      ❌ Error en fila {index}: {row_error}")

        conn.commit()
        cur.close()
        conn.close()
        print(f" [✅] Carga completada. {rows_inserted} pedidos importados.")
        return True

    except Exception as e:
        print(f" [!] Error crítico procesando archivo: {e}")
        return False

def main():
    # Asegurar directorios
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(ERROR_DIR, exist_ok=True)
    
    print(" [*] Legacy Watcher iniciado. Monitoreando carpeta /inbox...")

    while True:
        # Escanear carpeta
        files = [f for f in os.listdir(INBOX_DIR) if f.endswith('.csv')]
        
        for filename in files:
            filepath = os.path.join(INBOX_DIR, filename)
            
            # Procesar
            success = process_csv(filepath)
            
            # Mover archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if success:
                dest = os.path.join(PROCESSED_DIR, f"{timestamp}_{filename}")
                shutil.move(filepath, dest)
                print(f" [->] Archivo movido a 'processed'")
            else:
                dest = os.path.join(ERROR_DIR, f"{timestamp}_{filename}")
                shutil.move(filepath, dest)
                print(f" [->] Archivo movido a 'error'")

        time.sleep(5)  # Esperar 5 segundos antes de volver a mirar

if __name__ == "__main__":
    main()