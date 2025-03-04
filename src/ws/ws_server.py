import asyncio
from aiohttp import web
from src.ws.ws_manager import WebSocketManager
from src.utils.common import login
from src.controllers.user_devices_controller import UserDevicesController
from src.controllers.devices_controller import DevicesController
from src.tcp.sender.events import send_notificacion
from datetime import datetime


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()
        self.periodic_tasks = (
            {}
        )  # Diccionario para almacenar tareas periódicas por user_id

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

        # Obtener dispositivos del usuario conectado
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
            self.periodic_tasks[user_id] = asyncio.create_task(
                self.send_devices_periodically(user_id)
            )

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
            if not any(
                client_info["userid"] == user_id
                for client_info in self.ws_manager.clients.values()
            ):
                self.periodic_tasks[user_id].cancel()
                del self.periodic_tasks[user_id]

        return ws

    async def http_handler(self, request):
        method = request.method
        path = request.path

        if path == "/api/sos" and method == "POST":
            return await self.handle_sos_request(request)
        elif path == "/api/update-icons" and method == "GET":
            asyncio.create_task(self.save_devices_init())
            return web.Response(text="Update icons successfully", status=200)

        return web.HTTPNotFound(reason="Route not found", status=404)

    async def send_devices_periodically(self, user_id):
        ud_controller = UserDevicesController()
        while True:
            user_devices_task = asyncio.create_task(
                asyncio.to_thread(ud_controller.get_devices, user_id)
            )
            await asyncio.sleep(5)
            user_devices = await user_devices_task
            # Crear un conjunto de deviceid para búsqueda rápida
            device_ids = {item["deviceid"] for item in user_devices}
            # Filtrar vehículos solo del usuario conectado
            devices = [
                obj for obj in self.ws_manager.devices if obj["id"] in device_ids
            ]
            # Enviar dispositivos a todas las conexiones del usuario
            await self.ws_manager.send_to_all_clients(user_id, {"devices": devices})

    async def save_devices_init(self):
        device_controller = DevicesController()
        devices = device_controller.get_devices()
        await self.ws_manager.save_devices(devices)

    async def handle_sos_request(self, request):
        data = await request.json()
        device_id = data.get("deviceid")

        if not device_id:
            return web.HTTPBadRequest(reason="Missing deviceid in request", status=400)

        found_device = next(
            (device for device in self.ws_manager.devices if device["id"] == device_id),
            None,
        )
        if not found_device:
            return web.HTTPNotFound(reason="Device not found", status=404)

        # Buscar usuarios asociados al dispositivo
        ud_controller = UserDevicesController()
        users = ud_controller.get_users(device_id)
        sos_data = {
            "deviceid": found_device["id"],
            "name": found_device["name"],
            "uniqueid": found_device["uniqueid"],
            "type": "sos",
            "eventtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": found_device["latitude"],
            "longitude": found_device["longitude"],
        }

        # Procesar la solicitud POST para /api/sos
        asyncio.create_task(send_notificacion(users, sos_data))
        asyncio.create_task(self.ws_manager.send_events(users, sos_data))

        return web.Response(text="SOS data received successfully", status=200)

    async def start(self):
        await self.save_devices_init()
        # Crear una aplicación web y agregar los manejadores de WebSocket y HTTP
        app = web.Application()
        app.router.add_get(
            "/", self.websocket_handler
        )  # Escuchar en la raíz para WebSocket
        app.router.add_route(
            "*", "/api/{tail:.*}", self.http_handler
        )  # Escuchar en /api para HTTP
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket Server running on ws://{self.host}:{self.port}/")
        print(f"HTTP API endpoint running on http://{self.host}:{self.port}/api")


# Ejemplo de uso
if __name__ == "__main__":
    server = WebSocketServer()
    asyncio.run(server.start())
