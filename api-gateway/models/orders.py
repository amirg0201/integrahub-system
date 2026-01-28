from pydantic import BaseModel

class OrderItem(BaseModel):
    product_id: str
    quantity: int

class OrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItem]