from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.orders import router as orders_router

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

app.include_router(orders_router)
