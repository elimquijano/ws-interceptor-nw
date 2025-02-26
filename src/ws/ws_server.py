from aiohttp import web
from .ws_manager import WebSocketManager
from ..utils.common import login

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()

    async def websocket_handler(self, request):
        # Extraer parámetros de la URL
        username = request.query.get('u')  # Sin valor por defecto
        password = request.query.get('p')  # Sin valor por defecto

        # Verificar si se proporcionaron username y password
        if not username or not password:
            print("Connection attempt without credentials")
            return web.HTTPForbidden(reason="Authentication required")

        auth = await login(username, password)
        if not auth:
            print("Authentication failed")
            return web.HTTPForbidden(reason="Authentication failed")
        
        print(f"New WebSocket client connected - Username: {username}")
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        await self.ws_manager.register(ws, username, password)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    print(f"Message received from {username}: {msg.data}")
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"Error in WebSocket: {ws.exception()}")
        finally:
            await self.ws_manager.unregister(ws)

        return ws

    async def start(self):
        app = web.Application()
        app.router.add_get('/', self.websocket_handler)  # Escuchar en la raíz
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket Server running on ws://{self.host}:{self.port}")
