from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm # <--- NUEVO

# Importamos routers y lógica de auth
from routers.orders import router as orders_router
from auth import validate_jwt, create_access_token, Token # <--- NUEVO

# --- CONFIGURACIÓN DE APP ---
app = FastAPI(title="IntegraHub API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. ENDPOINT DE LOGIN (OBLIGATORIO PARA 4.3) ---
@app.post("/token", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Genera un token JWT si el usuario y contraseña son correctos.
    Credenciales Hardcoded para Demo: admin / secret
    """
    if form_data.username == "admin" and form_data.password == "secret":
        # Generamos el token usando la función de auth.py
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos",
        headers={"WWW-Authenticate": "Bearer"},
    )

# --- 2. HEALTH CHECK ---
health_router = APIRouter(tags=["Health"])
@health_router.get("/health/")
async def health_check():
    return {"status": "ok", "api": "ok", "rabbitmq": "unknown", "workers": "unknown"}
app.include_router(health_router)

# --- 3. RUTAS PROTEGIDAS (ORDERS) ---
# Aquí inyectamos la dependencia 'validate_jwt' para proteger TODAS las rutas de orders
app.include_router(
    orders_router,
    dependencies=[Depends(validate_jwt)] # <--- ESTO PROTEGE LA API
)

# --- 4. FRONTEND ---
current_file = Path(__file__).resolve()
current_dir = current_file.parent
docker_path = current_dir / "frontend-portal"
local_path = current_dir.parent / "frontend-portal"
static_dir = docker_path if docker_path.exists() else (local_path if local_path.exists() else None)

if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")