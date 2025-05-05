import asyncio
from aiohttp import web
from src.ws.ws_manager import WebSocketManager
from src.utils.common import login
from src.controllers.user_devices_controller import UserDevicesController
from src.controllers.devices_controller import DevicesController
from src.tcp.sender.events import Events
from datetime import datetime, timedelta
import uuid


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()
        self.periodic_tasks = {}
        self.guest_tokens = {}

    async def websocket_handler(self, request):
        # Extraer parámetros de la URL
        username = request.query.get("u")  # Sin valor por defecto
        password = request.query.get("p")  # Sin valor por defecto

        # Verificar si se proporcionaron username y password
        if not username or not password:
            # print("Connection attempt without credentials")
            return web.HTTPForbidden(reason="Authentication required")

        auth = login(username, password)
        if not auth:
            # print("Authentication failed")
            return web.HTTPForbidden(reason="Authentication failed")

        # Obtener dispositivos del usuario conectado
        user_id = auth["id"]
        ud_controller = UserDevicesController()
        user_devices = await asyncio.to_thread(ud_controller.get_devices, user_id)
        # Crear un conjunto de deviceid para búsqueda rápida
        device_ids = {item["deviceid"] for item in user_devices}
        # Filtrar vehículos solo del usuario conectado
        devices = [obj for obj in self.ws_manager.devices if obj["id"] in device_ids]
        # print(f"New WebSocket client connected - Username: {username}")

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

    async def guest_websocket_handler(self, request):
        token = request.query.get("t")

        if not token or token not in self.guest_tokens:
            # print("Invalid or expired token")
            return web.HTTPForbidden(reason="Invalid or expired token")

        guest_info = self.guest_tokens[token]
        if guest_info["expires_at"] < datetime.now():
            # print("Token has expired")
            return web.HTTPForbidden(reason="Token has expired")

        device_id = guest_info["deviceid"]
        devices = [
            obj for obj in self.ws_manager.devices if str(obj["id"]) == str(device_id)
        ]
        # print(f"New Guest WebSocket client connected - Token: {token}")

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self.ws_manager.register_guest(ws, token)

        await self.ws_manager.send_to_client(ws, {"devices": devices})

        if token not in self.periodic_tasks:
            self.periodic_tasks[token] = asyncio.create_task(
                self.send_device_periodically_to_guest(token, device_id)
            )

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    print(f"Message received from guest {token}: {msg.data}")
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"Error in Guest WebSocket: {ws.exception()}")
        except Exception as e:
            print(f"Exception in Guest WebSocket handler: {e}")
        finally:
            await self.ws_manager.unregister_guest(ws)
            if not any(
                guest_info["token"] == token
                for guest_info in self.ws_manager.guest_clients.values()
            ):
                self.periodic_tasks[token].cancel()
                del self.periodic_tasks[token]

        return ws

    async def http_handler(self, request):
        method = request.method
        path = request.path

        if path == "/api/sos" and method == "POST":
            return await self.handle_sos_request(request)
        elif path == "/api/update-devices" and method == "GET":
            asyncio.create_task(self.save_devices_init())
            return web.Response(text="Vehiculos actualizados correctamente", status=200)
        elif path == "/api/share" and method == "POST":
            return await self.handle_share_request(request)

        return web.HTTPNotFound(reason="Ruta no encontrada", status=404)

    async def send_devices_periodically(self, user_id):
        ud_controller = UserDevicesController()
        while True:
            user_devices_task = asyncio.create_task(
                asyncio.to_thread(ud_controller.get_devices, user_id)
            )
            await asyncio.sleep(5)
            user_devices = await user_devices_task
            device_ids = {item["deviceid"] for item in user_devices}
            devices = [
                obj for obj in self.ws_manager.devices if obj["id"] in device_ids
            ]
            await self.ws_manager.send_to_all_clients(user_id, {"devices": devices})

    async def send_device_periodically_to_guest(self, token, device_id):
        while True:
            await asyncio.sleep(5)
            devices = [
                obj
                for obj in self.ws_manager.devices
                if str(obj["id"]) == str(device_id)
            ]
            await self.ws_manager.send_to_all_guest_clients(token, {"devices": devices})

    async def save_devices_init(self):
        device_controller = DevicesController()
        devices = device_controller.get_devices()
        await self.ws_manager.save_devices(devices)

    async def handle_sos_request(self, request):
        data = await request.json()
        device_id = data.get("deviceid")

        if not device_id:
            return web.HTTPBadRequest(
                reason="Falta el deviceid en la solicitud", status=400
            )

        found_device = next(
            (
                device
                for device in self.ws_manager.devices
                if str(device["id"]) == str(device_id)
            ),
            None,
        )
        if not found_device:
            return web.HTTPNotFound(reason="Vehiculo no encontrado", status=404)

        e = Events()
        asyncio.create_task(e.create_event(found_device, "sos"))

        return web.Response(text="Evento SOS creado correctamente", status=200)

    async def handle_share_request(self, request):
        data = await request.json()
        device_id = data.get("deviceid")
        expires_at = data.get("expires_at")
        username = data.get("usuario")
        password = data.get("contraseña")

        if not device_id or not expires_at or not username or not password:
            return web.HTTPBadRequest(reason="Faltan campos requeridos", status=400)

        try:
            expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return web.HTTPBadRequest(reason="Formato de fecha incorrecto", status=400)

        auth = login(username, password)
        if not auth:
            return web.HTTPForbidden(reason="Authentication failed")

        user_id = auth["id"]
        ud_controller = UserDevicesController()
        user_devices = await asyncio.to_thread(ud_controller.get_devices, user_id)
        device_ids = {item["deviceid"] for item in user_devices}

        if int(device_id) not in device_ids:
            return web.HTTPForbidden(reason="Device not found for the user")

        token = str(uuid.uuid4())
        self.guest_tokens[token] = {"deviceid": device_id, "expires_at": expires_at}

        asyncio.create_task(self.remove_expired_guest(token, expires_at))

        return web.json_response({"token": token})

    async def remove_expired_guest(self, token, expires_at):
        await asyncio.sleep((expires_at - datetime.now()).total_seconds())
        if token in self.guest_tokens:
            del self.guest_tokens[token]
            # print(f"Guest token {token} has expired and been removed.")
            # Desconectar a todos los clientes invitados con este token
            for websocket, guest_info in list(self.ws_manager.guest_clients.items()):
                if guest_info["token"] == token:
                    await websocket.close(code=1000, message="Token expired")
                    await self.ws_manager.unregister_guest(websocket)

    async def update_device_status(self):
        """
        Tarea periódica que revisa el estado de los dispositivos basándose
        en su último tiempo de actualización.
        """
        while True:
            await asyncio.sleep(300)  # Esperar 5 minutos
            current_time = datetime.now()
            devices_updated = 0
            offline_threshold = timedelta(minutes=5)

            for device in self.ws_manager.devices:
                device_id = device.get("id", "ID Desconocido")  # Para logging útil
                last_update_str = device.get("lastupdate")
                current_status = device.get("status")  # Obtener estado actual

                new_status = None  # Para rastrear si el estado necesita cambiar
                needs_event = False

                if last_update_str is None:
                    # Si nunca hubo update, marcar como offline si no lo está ya
                    if current_status != "offline":
                        new_status = "offline"
                else:
                    try:
                        # Convertir last_update_str a datetime
                        last_update_time = datetime.strptime(
                            last_update_str, "%Y-%m-%d %H:%M:%S"
                        )
                        time_difference = current_time - last_update_time
                        if time_difference > offline_threshold:
                            # Excedió el umbral, debería estar offline
                            if current_status == "online":
                                # ¡Transición! Estaba online, ahora pasa a offline
                                new_status = "offline"
                                needs_event = True
                                print(
                                    f"Dispositivo {device_id} transicionó a offline (última act: {last_update_str})."
                                )
                            elif current_status != "offline":
                                # No estaba 'online' (quizás 'None' u otro estado), pero debería ser 'offline'
                                new_status = "offline"
                                print(
                                    f"Dispositivo {device_id} marcado como offline (estado previo: {current_status}, última act: {last_update_str})."
                                )
                            # else: ya estaba offline, no hacer nada con el estado

                        else:
                            # Dentro del umbral, debería estar online
                            if current_status != "online":
                                new_status = "online"
                                # No se genera evento al pasar a online (según lógica original)
                                print(
                                    f"Dispositivo {device_id} marcado/confirmado como online (última act: {last_update_str})."
                                )
                            # else: ya estaba online, no hacer nada con el estado

                    except ValueError:
                        # Error al parsear la fecha
                        print(
                            f"Formato de fecha inválido '{last_update_str}' para dispositivo {device_id}. Marcando como offline."
                        )
                        if current_status != "offline":
                            new_status = "offline"

                # Aplicar cambios si es necesario
                if new_status is not None:
                    devices_updated += 1
                    device["status"] = new_status
                    if new_status == "offline":
                        device["speed"] = 0.0
                    # Crear evento SÓLO si hubo transición online -> offline
                    if needs_event:
                        e = Events()
                        asyncio.create_task(e.create_event(device, "deviceOffline"))

            print(
                f"Ciclo de actualización completado. {devices_updated} dispositivos actualizados."
            )

    async def start(self):
        await self.save_devices_init()
        asyncio.create_task(self.update_device_status())
        app = web.Application()
        app.router.add_get("/", self.websocket_handler)
        app.router.add_get("/guest", self.guest_websocket_handler)
        app.router.add_route("*", "/api/{tail:.*}", self.http_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket Server running on ws://{self.host}:{self.port}/")
        print(f"HTTP API endpoint running on http://{self.host}:{self.port}/api")
