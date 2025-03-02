import asyncio
from aiohttp import web
from src.ws.ws_manager import WebSocketManager
from src.utils.common import login
from src.controllers.user_devices_controller import UserDevicesController
from src.controllers.devices_controller import DevicesController

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()
        self.periodic_tasks = {}  # Diccionario para almacenar tareas periódicas por user_id

    async def websocket_handler(self, request):
        # Extraer parámetros de la URL
        username = request.query.get("u")  # Sin valor por defecto
        password = request.query.get("p")  # Sin valor por defecto

        # Verificar si se proporcionaron username y password
        if not username or not password:
            print("Connection attempt without credentials")
            return web.HTTPForbidden(reason="Authentication required")

        auth = login(username, password)
        if not auth:
            print("Authentication failed")
            return web.HTTPForbidden(reason="Authentication failed")

        user_id = auth["id"]
        ud_controller = UserDevicesController()
        user_devices = await asyncio.to_thread(ud_controller.get_devices, user_id)
        # Crear un conjunto de deviceid para búsqueda rápida
        device_ids = {item["deviceid"] for item in user_devices}
        # Filtrar vehículos solo del usuario conectado
        devices = [obj for obj in self.ws_manager.devices if obj["id"] in device_ids]
        print(f"New WebSocket client connected - Username: {username}")

        ws = web.WebSocketResponse()
        await ws.prepare(request)  # Preparar el WebSocket antes de registrarlo
        await self.ws_manager.register(ws, username, password, user_id)

        # Enviar dispositivos al cliente
        await self.ws_manager.send_to_client(ws, {"devices": devices})

        # Iniciar la tarea en segundo plano para enviar dispositivos cada 5 segundos
        if user_id not in self.periodic_tasks:
            self.periodic_tasks[user_id] = asyncio.create_task(self.send_devices_periodically(user_id))

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    print(f"Message received from {username}: {msg.data}")
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"Error in WebSocket: {ws.exception()}")
        except Exception as e:
            print(f"Exception in WebSocket handler: {e}")
        finally:
            await self.ws_manager.unregister(ws)
            # Si no hay más conexiones para este usuario, cancelar la tarea periódica
            if not any(client_info["userid"] == user_id for client_info in self.ws_manager.clients.values()):
                self.periodic_tasks[user_id].cancel()
                del self.periodic_tasks[user_id]

        return ws

    async def send_devices_periodically(self, user_id):
        ud_controller = UserDevicesController()
        while True:
            user_devices_task = asyncio.create_task(asyncio.to_thread(ud_controller.get_devices, user_id))
            await asyncio.sleep(5)
            user_devices = await user_devices_task
            # Crear un conjunto de deviceid para búsqueda rápida
            device_ids = {item["deviceid"] for item in user_devices}
            # Filtrar vehículos solo del usuario conectado
            devices = [obj for obj in self.ws_manager.devices if obj["id"] in device_ids]
            # Enviar dispositivos a todas las conexiones del usuario
            await self.ws_manager.send_to_all_clients(user_id, {"devices": devices})

    async def save_devices_init(self):
        device_controller = DevicesController()
        devices = device_controller.get_devices()
        await self.ws_manager.save_devices(devices)

    async def start(self):
        await self.save_devices_init()
        # Crear una aplicación web y agregar el manejador de WebSocket
        app = web.Application()
        app.router.add_get("/", self.websocket_handler)  # Escuchar en la raíz
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket Server running on ws://{self.host}:{self.port}")
