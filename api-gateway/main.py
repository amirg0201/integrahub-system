from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importamos el router con la lógica de RabbitMQ y Seguridad
from routers.orders import router as orders_router

app = FastAPI(
    title="IntegraHub API Gateway",
    version="1.0.0",
    description="Punto de entrada para pedidos (Event-Driven)"
)

# --- 1. Configuración CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Rutas de API ---
# Es importante registrar esto ANTES de montar los archivos estáticos
app.include_router(orders_router)

# --- 3. Servir Frontend (Solución al error Not Found) ---
# Detectamos dónde está la carpeta 'frontend-portal' dinámicamente

current_file = Path(__file__).resolve()
current_dir = current_file.parent

# Ruta A: Dentro de Docker (según tu docker-compose montamos en /app/frontend-portal)
docker_path = current_dir / "frontend-portal"

# Ruta B: En tu PC Local (la carpeta está un nivel arriba, hermana de api-gateway)
local_path = current_dir.parent / "frontend-portal"

# Verificamos cuál existe
if docker_path.exists():
    static_dir = docker_path
    print(f"✅ Frontend detectado en modo Docker: {static_dir}")
elif local_path.exists():
    static_dir = local_path
    print(f"✅ Frontend detectado en modo Local: {static_dir}")
else:
    static_dir = None
    print(f"⚠️ ERROR: No se encontró la carpeta 'frontend-portal'. Buscado en: {docker_path} y {local_path}")

# Montamos la carpeta si la encontramos
if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")