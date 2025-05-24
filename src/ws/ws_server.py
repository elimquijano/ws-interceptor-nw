import asyncio
import logging
from datetime import datetime, timedelta
import uuid
import json
from aiohttp import web

from src.ws.ws_manager import WebSocketManager
from src.utils.common import login
from src.controllers.user_devices_controller import UserDevicesController
from src.tcp.sender.events import EventNotifierService

logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=7006):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()  # Singleton
        self.periodic_tasks_per_user = {}
        self.periodic_ud_controllers = (
            {}
        )  # Almacena UserDevicesController por user_id para tareas periódicas
        self.periodic_tasks_per_guest_token = {}
        self.guest_tokens_active = {}
        self.app_runner = None
        self.event_notifier = EventNotifierService(self.ws_manager)
        logger.info("WebSocketServer instanciado.")

    async def websocket_handler(self, request):
        username = request.query.get("u")
        password = request.query.get("p")
        if not username or not password:
            logger.warning("Conexión WS: Sin credenciales.")
            return web.HTTPForbidden(reason="Auth required")

        auth_result = await asyncio.to_thread(login, username, password)
        if not auth_result:
            logger.warning(f"Conexión WS: Auth fallida para {username}.")
            return web.HTTPForbidden(reason="Auth failed")

        user_id = auth_result["id"]

        # Usar un UserDevicesController local para la carga inicial
        initial_load_udc = UserDevicesController()
        try:
            user_device_assignments = await asyncio.to_thread(
                initial_load_udc.get_devices, user_id
            )
        except Exception as e:
            logger.error(
                f"Error obteniendo dispositivos para user {user_id} (conexión inicial): {e}",
                exc_info=True,
            )
            return web.HTTPInternalServerError(reason="Error retrieving user devices")
        finally:
            await asyncio.to_thread(initial_load_udc.close)  # Cerrar UDC local

        device_ids_assigned_to_user = {
            item["deviceid"] for item in user_device_assignments or []
        }
        all_cached_devices = (
            self.ws_manager.get_all_devices()
        )  # Usa self.ws_manager.devices
        devices_for_this_client = [
            dev
            for dev in all_cached_devices
            if dev.get("id") in device_ids_assigned_to_user
        ]

        logger.info(f"Cliente WebSocket conectado: {username} (ID: {user_id})")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self.ws_manager.register(ws, username, password, user_id)
        await self.ws_manager.send_to_client(ws, {"devices": devices_for_this_client})

        if user_id not in self.periodic_tasks_per_user:
            if user_id not in self.periodic_ud_controllers:
                # Crear y almacenar UDC si no existe para esta tarea periódica de usuario
                self.periodic_ud_controllers[user_id] = UserDevicesController()
                logger.debug(
                    f"Nueva instancia de UserDevicesController creada para tarea periódica del user {user_id}"
                )

            udc_for_task = self.periodic_ud_controllers[
                user_id
            ]  # Usar la instancia almacenada
            self.periodic_tasks_per_user[user_id] = asyncio.create_task(
                self._send_devices_periodically_to_user(user_id, udc_for_task)
            )

        client_description = f"{username} (User ID: {user_id})"
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    logger.info(f"Mensaje de {client_description}: {msg.data}")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(
                        f"Error en WS para {client_description}: {ws.exception()}",
                        exc_info=True,
                    )
        except asyncio.CancelledError:
            logger.info(f"Conexión WS para {client_description} cancelada.")
        except Exception as e:
            logger.info(
                f"Excepción/Desconexión en WS para {client_description}: {type(e).__name__} - {e}"
            )
        finally:
            unregistered_info = await self.ws_manager.unregister(ws)
            if unregistered_info:
                logger.info(
                    f"Cliente desconectado: {unregistered_info.get('username')}"
                )

            if user_id:
                is_last_client_for_user = not any(
                    c_info.get("userid") == user_id
                    for c_info in self.ws_manager.clients.values()
                )
                if is_last_client_for_user and user_id in self.periodic_tasks_per_user:
                    task_to_cancel = self.periodic_tasks_per_user.pop(user_id)
                    task_to_cancel.cancel()
                    try:
                        await task_to_cancel
                    except asyncio.CancelledError:
                        pass  # Esperado

                    if user_id in self.periodic_ud_controllers:
                        udc_to_close = self.periodic_ud_controllers.pop(user_id)
                        logger.info(
                            f"Cerrando UserDevicesController de tarea periódica para user {user_id}."
                        )
                        await asyncio.to_thread(udc_to_close.close)
                    logger.info(
                        f"Tarea periódica y UDC asociado detenidos para user_id: {user_id}"
                    )
        return ws

    async def guest_websocket_handler(self, request):
        token = request.query.get("t")
        if not token or token not in self.guest_tokens_active:
            return web.HTTPForbidden(reason="Invalid or expired token")
        guest_token_details = self.guest_tokens_active[token]
        if guest_token_details["expires_at"] < datetime.now():
            if token in self.guest_tokens_active:
                del self.guest_tokens_active[token]
            return web.HTTPForbidden(reason="Token has expired")
        device_id_for_guest = guest_token_details["deviceid"]
        device_for_guest_payload = []
        found_device_obj = self.ws_manager.get_device_by_id(int(device_id_for_guest))
        if found_device_obj:
            device_for_guest_payload.append(found_device_obj)
        logger.info(
            f"Cliente WS invitado conectado: Token {token} para DevID {device_id_for_guest}"
        )
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await self.ws_manager.register_guest(ws, token)
        await self.ws_manager.send_to_client(ws, {"devices": device_for_guest_payload})
        if token not in self.periodic_tasks_per_guest_token:
            self.periodic_tasks_per_guest_token[token] = asyncio.create_task(
                self._send_device_periodically_to_guest(token, device_id_for_guest)
            )
        guest_description = f"Invitado (Token: {token})"
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    logger.info(f"Mensaje de {guest_description}: {msg.data}")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(
                        f"Error en WS para {guest_description}: {ws.exception()}",
                        exc_info=True,
                    )
        except asyncio.CancelledError:
            logger.info(f"Conexión WS para {guest_description} cancelada.")
        except Exception as e:
            logger.info(
                f"Excepción/Desconexión en WS para {guest_description}: {type(e).__name__} - {e}"
            )
        finally:
            unregistered_guest = await self.ws_manager.unregister_guest(ws)
            if unregistered_guest:
                logger.info(f"Invitado desconectado: {unregistered_guest.get('token')}")
            if not any(
                g_info.get("token") == token
                for g_info in self.ws_manager.guest_clients.values()
            ):
                if token in self.periodic_tasks_per_guest_token:
                    task_to_cancel = self.periodic_tasks_per_guest_token.pop(token)
                    task_to_cancel.cancel()
                    await asyncio.sleep(0)  # Permitir que la cancelación se propague
                    try:
                        await task_to_cancel
                    except asyncio.CancelledError:
                        pass
                    logger.info(
                        f"Tarea periódica detenida para token invitado: {token}"
                    )
        return ws

    async def http_handler(self, request):
        method = request.method
        path = request.path
        if path == "/api/sos" and method == "POST":
            return await self._handle_sos_request(request)
        if path == "/api/update-devices" and method == "GET":
            asyncio.create_task(self.ws_manager._update_selective_devices_cache())
            return web.Response(text="Actualización iniciada.", status=202)
        if path == "/api/share" and method == "POST":
            return await self._handle_share_request(request)
        return web.HTTPNotFound(reason="Ruta no encontrada")

    async def _send_devices_periodically_to_user(
        self, user_id: int, ud_controller: UserDevicesController
    ):
        """Envía periódicamente la lista de dispositivos a un usuario, usando el ud_controller provisto."""
        logger.info(f"Iniciando tarea periódica de envío para user {user_id}.")
        try:
            while True:
                user_device_assignments_task = asyncio.create_task(
                    asyncio.to_thread(ud_controller.get_devices, user_id)
                )
                await asyncio.sleep(5)
                user_device_assignments = await user_device_assignments_task

                if user_device_assignments is None:
                    logger.warning(
                        f"No se pudieron obtener dispositivos para user {user_id} en tarea periódica. Reintentando en 30s."
                    )
                    await asyncio.sleep(25)
                    continue

                device_ids_assigned_to_user = {
                    item["deviceid"] for item in user_device_assignments
                }
                all_cached_devices = self.ws_manager.get_all_devices()
                devices_for_this_client = [
                    dev
                    for dev in all_cached_devices
                    if dev.get("id") in device_ids_assigned_to_user
                ]

                await self.ws_manager.send_to_all_clients_by_userid(
                    user_id, {"devices": devices_for_this_client}
                )
        except asyncio.CancelledError:
            logger.info(f"Tarea periódica de envío para user {user_id} cancelada.")
        except Exception as e:
            logger.error(
                f"Error crítico en _send_devices_periodically_to_user para user {user_id}: {e}",
                exc_info=True,
            )

    async def _send_device_periodically_to_guest(self, token: str, device_id: int):
        try:
            target_device_id_int = int(device_id)
        except (ValueError, TypeError):
            logger.error(f"DeviceID inválido '{device_id}' para token {token}")
            return
        logger.info(
            f"Iniciando tarea periódica envío invitado (token: {token}, deviceID: {device_id})"
        )
        try:
            while True:
                await asyncio.sleep(5)
                dev_payload = []
                found_dev = self.ws_manager.get_device_by_id(target_device_id_int)
                if found_dev:
                    dev_payload.append(found_dev)
                await self.ws_manager.send_to_all_guest_clients_by_token(
                    token, {"devices": dev_payload}
                )
        except asyncio.CancelledError:
            logger.info(f"Tarea periódica envío invitado (token {token}) cancelada.")
        except Exception as e:
            logger.error(
                f"Error en _send_device_periodically_to_guest ({token}): {e}",
                exc_info=True,
            )

    async def _handle_sos_request(self, request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.HTTPBadRequest(reason="JSON inválido.")
        dev_id_str = data.get("deviceid")
        if not dev_id_str:
            return web.HTTPBadRequest(reason="Falta deviceid")
        try:
            dev_id = int(dev_id_str)
        except ValueError:
            return web.HTTPBadRequest(reason="deviceid debe ser entero.")
        found_device = self.ws_manager.get_device_by_id(dev_id)
        if not found_device:
            return web.HTTPNotFound(reason="Vehículo no encontrado")

        # Añadir dispositivo a usuarios cercanos de soporte
        await self.ws_manager.add_vehicle_to_nearby_support_users_task(found_device)

        # Crear evento SOS
        asyncio.create_task(
            self.event_notifier.create_and_notify_custom_event(found_device, "sos")
        )
        return web.Response(text="Evento SOS creado", status=200)

    async def _handle_share_request(self, request):
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.HTTPBadRequest(reason="JSON inválido.")
        dev_id_str = data.get("deviceid")
        exp_at_str = data.get("expires_at")
        uname = data.get("usuario")
        pwd = data.get("contraseña")
        if not all([dev_id_str, exp_at_str, uname, pwd]):
            return web.HTTPBadRequest(reason="Faltan campos")
        try:
            dev_id = int(dev_id_str)
            exp_dt = datetime.strptime(exp_at_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return web.HTTPBadRequest(reason="Formato deviceid/fecha incorrecto")
        auth = await asyncio.to_thread(login, uname, pwd)
        if not auth:
            return web.HTTPForbidden(reason="Autenticación fallida")
        uid = auth["id"]
        local_udc = UserDevicesController()
        try:
            user_devs = await asyncio.to_thread(local_udc.get_devices, uid)
        finally:
            await asyncio.to_thread(local_udc.close)
        user_dev_ids = {item["deviceid"] for item in user_devs or []}
        if dev_id not in user_dev_ids:
            return web.HTTPForbidden(reason="Dispositivo no autorizado")
        token = str(uuid.uuid4())
        self.guest_tokens_active[token] = {"deviceid": dev_id, "expires_at": exp_dt}
        asyncio.create_task(self._schedule_guest_token_removal(token, exp_dt))
        return web.json_response({"token": token})

    async def _schedule_guest_token_removal(self, token: str, expires_at: datetime):
        delay = (expires_at - datetime.now()).total_seconds()
        if delay <= 0:
            await self._remove_guest_token_and_disconnect(token)
            return
        await asyncio.sleep(delay)
        await self._remove_guest_token_and_disconnect(token)

    async def _remove_guest_token_and_disconnect(self, token: str):
        if token in self.guest_tokens_active:
            del self.guest_tokens_active[token]
        for ws, guest_info in list(self.ws_manager.guest_clients.items()):
            if guest_info.get("token") == token:
                try:
                    await ws.close(code=1000, message="Token expired")
                except Exception:
                    pass

    async def _update_device_online_status_periodically(self):
        offline_thresh = timedelta(minutes=10)
        check_interval = 60
        logger.info(
            f"Iniciando tarea periódica de estado online/offline (intervalo: {check_interval}s)."
        )
        try:
            while True:
                await asyncio.sleep(check_interval)
                now = datetime.now()
                for dev in self.ws_manager.get_all_devices():
                    last_up = dev.get("lastupdate")
                    cur_stat = dev.get("status")
                    new_stat = None
                    notify_offline = False
                    if last_up is None:
                        if cur_stat != "offline":
                            new_stat = "offline"
                    else:
                        try:
                            last_up_dt = datetime.strptime(last_up, "%Y-%m-%d %H:%M:%S")
                            if (now - last_up_dt) > offline_thresh:
                                if cur_stat != "offline":
                                    new_stat = "offline"
                                if cur_stat == "online":
                                    notify_offline = True
                            else:
                                if cur_stat != "online":
                                    new_stat = "online"
                        except ValueError:
                            if cur_stat != "offline":
                                new_stat = "offline"
                    if new_stat is not None:
                        dev["status"] = new_stat
                        if new_stat == "offline":
                            dev["speed"] = 0.0
                        if notify_offline:
                            asyncio.create_task(
                                self.event_notifier.create_and_notify_custom_event(
                                    dev, "deviceOffline"
                                )
                            )
        except asyncio.CancelledError:
            logger.info("Tarea de actualización de estado de dispositivos cancelada.")
        except Exception as e:
            logger.error(
                f"Error crítico en _update_device_online_status_periodically: {e}",
                exc_info=True,
            )

    async def start(self):
        await self.ws_manager._load_initial_devices_cache()
        asyncio.create_task(self._update_device_online_status_periodically())
        app = web.Application()
        app.router.add_get("/", self.websocket_handler)
        app.router.add_get("/guest", self.guest_websocket_handler)
        app.router.add_route("*", "/api/{tail:.*}", self.http_handler)
        self.app_runner = web.AppRunner(app)
        await self.app_runner.setup()
        site = web.TCPSite(self.app_runner, self.host, self.port)
        try:
            await site.start()
            logger.info(f"Servidor WS/HTTP en http://{self.host}:{self.port}")
            # El bucle de servir para siempre se maneja por la tarea principal en main.py
            # que espera a esta tarea. Para que esta tarea no termine inmediatamente:
            await asyncio.Event().wait()  # Espera hasta que se cancele
        except asyncio.CancelledError:
            logger.info("Servidor WebSocket/HTTP (site.start loop) cancelado.")
