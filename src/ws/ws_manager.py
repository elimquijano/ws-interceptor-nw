import json
import asyncio
from datetime import datetime


class WebSocketManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.clients = {}  # Dict[websocket, dict]
            cls._instance.guest_clients = {}  # Dict[websocket, dict]
            cls._instance.devices = []  # Dict[dict]
        return cls._instance

    async def register(self, websocket, username, password, userid):
        self.clients[websocket] = {
            "username": username,
            "password": password,
            "userid": userid,
        }
        print(f"Client registered: {username}")

    async def unregister(self, websocket):
        if websocket in self.clients:
            username = self.clients[websocket]["username"]
            del self.clients[websocket]
            print(f"Client disconnected: {username}")

    async def register_guest(self, websocket, token):
        self.guest_clients[websocket] = {"token": token}
        print(f"Guest registered: {token}")

    async def unregister_guest(self, websocket):
        if websocket in self.guest_clients:
            token = self.guest_clients[websocket]["token"]
            del self.guest_clients[websocket]
            print(f"Guest disconnected: {token}")

    async def send_to_client(self, websocket, message):
        if websocket not in self.clients and websocket not in self.guest_clients:
            print(f"WebSocket not found for the client.")
            return

        try:
            # Convertir objetos datetime a cadenas de texto
            message = self.serialize_datetime(message)
            await websocket.send_str(json.dumps(message))
            client_info = self.clients.get(websocket) or self.guest_clients.get(
                websocket
            )
            client_identifier = client_info.get("username") or client_info.get("token")
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Message sent to {client_identifier}"
            )
        except Exception as e:
            print(f"Error sending to {client_identifier}: {e}")
            if websocket in self.clients:
                await self.unregister(websocket)
            elif websocket in self.guest_clients:
                await self.unregister_guest(websocket)

    async def send_to_all_clients(self, user_id, message):
        tasks = []
        for websocket, client_info in self.clients.items():
            if client_info["userid"] == user_id:
                tasks.append(self.send_to_client(websocket, message))
        await asyncio.gather(*tasks)

    async def send_to_all_guest_clients(self, token, message):
        tasks = []
        for websocket, guest_info in self.guest_clients.items():
            if guest_info["token"] == token:
                tasks.append(self.send_to_client(websocket, message))
        await asyncio.gather(*tasks)

    async def save_devices(self, devices):
        self.devices = devices

    async def send_events(self, users, event):
        for user in users:
            await self.send_to_all_clients(user["userid"], {"event": event})

    def serialize_datetime(self, obj):
        if isinstance(obj, list):
            return [self.serialize_datetime(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
