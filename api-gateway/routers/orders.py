from fastapi import APIRouter, Depends, HTTPException
import uuid

from models.orders import OrderRequest
from core.security import validate_jwt
from core.rabbitmq import publish_event

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("", status_code=202)
async def create_order(
    order: OrderRequest,
    token_payload: dict = Depends(validate_jwt)
):
    order_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "OrderCreated",
        "correlation_id": correlation_id,
        "data": {
            "order_id": order_id,
            "customer_id": order.customer_id,
            "items": [item.model_dump() for item in order.items]
        }
    }

    try:
        await publish_event(event, "order.created")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error publicando evento: {str(e)}"
        )

    return {
        "message": "Pedido recibido",
        "order_id": order_id,
        "correlation_id": correlation_id,
        "status": "PROCESSING"
    }
