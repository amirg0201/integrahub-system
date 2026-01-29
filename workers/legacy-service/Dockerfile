# Usamos una versión ligera de Python
FROM python:3.11-slim

# Evita que Python guarde archivos .pyc y fuerza los logs a salir en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# 1. Copiamos y e instalamos requerimientos primero (para aprovechar caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Creamos las carpetas necesarias para el proceso
# Aunque mapeamos "inbox" desde fuera, es bueno que existan las de destino
RUN mkdir -p /app/inbox /app/processed /app/error

# 3. Copiamos el resto del código (el worker.py)
COPY . .

# Comando para iniciar el worker
CMD ["python", "worker.py"]