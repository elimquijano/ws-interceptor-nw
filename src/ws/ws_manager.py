import json
from datetime import datetime


class WebSocketManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.clients = {}  # Dict[websocket, dict]
            cls._instance.devices = []  # Dict[dict]
        return cls._instance

    async def register(self, websocket, username, password):
        self.clients[websocket] = {"username": username, "password": password}
        print(f"Client registered: {username}")

    async def unregister(self, websocket):
        if websocket in self.clients:
            username = self.clients[websocket]["username"]
            del self.clients[websocket]
            print(f"Client disconnected: {username}")

    async def send_to_client(self, websocket, message):
        if websocket not in self.clients:
            print(f"WebSocket not found for the client.")
            return

        try:
            # Convertir objetos datetime a cadenas de texto
            message = self.serialize_datetime(message)
            await websocket.send_str(json.dumps(message))
            print(f"Message sent to {self.clients[websocket]['username']}")
        except Exception as e:
            print(f"Error sending to {self.clients[websocket]['username']}: {e}")
            await self.unregister(websocket)

    async def save_devices(self, devices):
        self.devices = devices
        print(f"Devices {len(self.devices)} saved successfully")

    def serialize_datetime(self, obj):
        if isinstance(obj, list):
            return [self.serialize_datetime(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
