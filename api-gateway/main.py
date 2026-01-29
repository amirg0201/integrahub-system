from pathlib import Path
from fastapi import FastAPI, APIRouter # <--- IMPORTANTE: Importar APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importamos el router de órdenes
from routers.orders import router as orders_router

# --- 1. DEFINICIÓN DEL HEALTH ROUTER (Lo que te faltaba) ---
health_router = APIRouter(tags=["Health"])

@health_router.get("/health/")
async def health_check():
    return {"status": "ok"}

# --- 2. Configuración de la APP ---
app = FastAPI(
    title="IntegraHub API Gateway",
    version="1.0.0",
    description="Punto de entrada para pedidos (Event-Driven)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Incluir Rutas ---
# Ahora sí existe 'health_router', así que esta línea ya no dará error
app.include_router(health_router)
app.include_router(orders_router)

# --- 4. Servir Frontend (Lógica estática) ---
current_file = Path(__file__).resolve()
current_dir = current_file.parent

docker_path = current_dir / "frontend-portal"
local_path = current_dir.parent / "frontend-portal"

if docker_path.exists():
    static_dir = docker_path
elif local_path.exists():
    static_dir = local_path
else:
    static_dir = None

if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")