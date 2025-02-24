import websockets
from typing import Dict, Set

class WebSocketManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.clients = {}  # Dict[websocket, dict]
        return cls._instance

    async def register(self, websocket, username, password):
        self.clients[websocket] = {
            "username": username,
            "password": password
        }

    async def unregister(self, websocket):
        if websocket in self.clients:
            username = self.clients[websocket]["username"]
            del self.clients[websocket]
            print(f"Client disconnected: {username}")

    async def broadcast(self, message):
        if not self.clients:
            print("No clients connected")
            return

        for ws, client_info in self.clients.items():
            try:
                await ws.send(str(message))
                print(f"Message sent to {client_info['username']}")
            except Exception as e:
                print(f"Error sending to {client_info['username']}: {e}")
                await self.unregister(ws)