import asyncio
import websockets
from urllib.parse import parse_qs
from .ws_manager import WebSocketManager

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()

    async def handle_client(self, websocket, path):
        # Parse query parameters
        query = parse_qs(path.lstrip('/?'))
        username = query.get('u', [None])[0]
        password = query.get('p', [None])[0]

        if not username or not password:
            print("Connection attempt without credentials")
            return

        print(f"New WebSocket client connected - Username: {username}")
        await self.ws_manager.register(websocket, username, password)
        
        try:
            async for _ in websocket:
                pass  # Just keep connection alive
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.ws_manager.unregister(websocket)

    async def start(self):
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        print(f"WebSocket Server running on ws://{self.host}:{self.port}")
        await server.wait_closed()