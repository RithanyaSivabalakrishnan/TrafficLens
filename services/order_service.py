import argparse
import uvicorn
from pydantic import BaseModel
from services.common import create_service_app

app = create_service_app("orders")

orders_db = [
    {"id": 101, "status": "processing"},
    {"id": 102, "status": "shipped"}
]

class OrderCreate(BaseModel):
    item: str
    quantity: int

@app.get("/orders")
async def get_orders():
    return {"orders": orders_db}

@app.post("/orders")
async def create_order(order: OrderCreate):
    new_order = {
        "id": 100 + len(orders_db) + 1,
        "item": order.item,
        "quantity": order.quantity,
        "status": "created"
    }
    orders_db.append(new_order)
    return new_order

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Order Service Microservice")
    parser.add_argument("--port", type=int, default=8003, help="Port to run Order Service on")
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
