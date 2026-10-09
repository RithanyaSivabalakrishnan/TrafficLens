import argparse
import uvicorn
from fastapi import Request
from pydantic import BaseModel
from services.common import create_service_app

app = create_service_app("users")

users_db = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
]

class UserCreate(BaseModel):
    name: str

@app.get("/users")
async def get_users():
    return {"users": users_db}

@app.post("/users")
async def create_user(user: UserCreate):
    new_user = {"id": len(users_db) + 1, "name": user.name}
    users_db.append(new_user)
    return new_user

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User Service Microservice")
    parser.add_argument("--port", type=int, default=8001, help="Port to run User Service on")
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
