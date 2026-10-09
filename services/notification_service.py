import uuid
import argparse
import uvicorn
from pydantic import BaseModel
from services.common import create_service_app

app = create_service_app("notifications")

class NotificationSend(BaseModel):
    recipient: str
    message: str

@app.post("/send")
async def send_notification(payload: NotificationSend):
    return {
        "queued": True,
        "notification_id": str(uuid.uuid4()),
        "recipient": payload.recipient
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notification Service Microservice")
    parser.add_argument("--port", type=int, default=8004, help="Port to run Notification Service on")
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
