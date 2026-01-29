FROM python:3.11-slim
WORKDIR /app

# Copiamos los requisitos primero para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código del worker
COPY worker.py .

# Comando de arranque
CMD ["python", "worker.py"]