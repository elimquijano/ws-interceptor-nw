import json
import aiohttp
import asyncio
from datetime import datetime
import logging
from src.controllers.devices_controller import DevicesController
from src.controllers.user_devices_controller import UserDevicesController
from src.utils.common import API_URL_ADMIN_NWPERU

logger = logging.getLogger(__name__)


class WebSocketManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance.clients = {}
            cls._instance.guest_clients = {}
            cls._instance.devices = (
                []
            )  # LA fuente de verdad para el estado de todos los dispositivos
            logger.info(
                "WebSocketManager instanciado (usando self.devices como lista principal)."
            )
        return cls._instance

    async def register(self, websocket, username, password, userid):
        self.clients[websocket] = {
            "username": username,
            "password": password,  # Considerar no almacenar passwords en memoria
            "userid": userid,
        }

    async def unregister(self, websocket):
        if websocket in self.clients:
            return self.clients.pop(websocket)  # Devuelve la info del cliente
        return None

    async def register_guest(self, websocket, token):
        self.guest_clients[websocket] = {"token": token}

    async def unregister_guest(self, websocket):
        if websocket in self.guest_clients:
            return self.guest_clients.pop(websocket)  # Devuelve la info del invitado
        return None

    async def send_to_client(self, websocket, message: dict):
        try:
            serialized_message = self._serialize_datetime_objects(message)
            await websocket.send_str(json.dumps(serialized_message))
        except ConnectionResetError:  # Cliente cerró abruptamente
            logger.debug(f"Conexión reseteada por cliente durante send_to_client.")
        except RuntimeError as e:  # ej. "WebSocket connection is closed."
            logger.debug(
                f"Error de Runtime enviando a cliente (probablemente cerrado): {e}"
            )
        except Exception as e:
            client_info = self.clients.get(websocket) or self.guest_clients.get(
                websocket
            )
            client_id = (
                client_info.get("username") or client_info.get("token", "Desconocido")
                if client_info
                else "Desconocido"
            )
            logger.error(
                f"Error inesperado enviando a cliente {client_id}: {e}", exc_info=True
            )

    async def send_to_all_clients_by_userid(self, user_id: int, message: dict):
        if not self.clients:
            return
        # Crear una copia de los items para iterar de forma segura
        tasks = [
            self.send_to_client(websocket, message)
            for websocket, client_info in list(self.clients.items())
            if client_info.get("userid") == user_id
        ]
        if tasks:
            # return_exceptions=True para que un error en un envío no detenga los demás
            await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_all_guest_clients_by_token(self, token: str, message: dict):
        if not self.guest_clients:
            return
        tasks = [
            self.send_to_client(websocket, message)
            for websocket, guest_info in list(self.guest_clients.items())
            if guest_info.get("token") == token
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_device_by_id(self, device_id: int) -> dict | None:
        try:
            target_id = int(device_id)
        except (ValueError, TypeError):
            return None
        for device in self.devices:
            if device.get("id") == target_id:
                return device
        return None

    def get_device_by_uniqueid(self, uniqueid: str) -> dict | None:
        target_uniqueid = str(uniqueid)  # Asegurar que es string para comparación
        for device in self.devices:
            if device.get("uniqueid") == target_uniqueid:
                return device
        return None

    def get_all_devices(self) -> list:
        """Devuelve la referencia a la lista interna self.devices."""
        return self.devices

    async def save_devices(self, new_devices_list: list[dict]):
        """Reemplaza la lista self.devices. Es el método principal para actualizar el caché."""
        if not isinstance(new_devices_list, list):
            logger.error(
                f"save_devices esperaba una lista, recibió {type(new_devices_list)}"
            )
            self.devices = (
                []
            )  # Evitar error si el tipo es incorrecto, dejar caché vacío
            return
        self.devices = new_devices_list
        # logger.debug(f"Caché self.devices actualizado con {len(self.devices)} dispositivos.")

    async def update_single_device_in_cache(self, device_data: dict):
        """Actualiza o añade un dispositivo en self.devices."""
        if not isinstance(device_data, dict):
            logger.warning(
                f"update_single_device_in_cache: device_data no es un dict: {device_data}"
            )
            return

        dev_id_to_update = device_data.get("id")
        if dev_id_to_update is None:
            logger.warning(
                f"Intento de actualizar/añadir dispositivo sin ID: {device_data}"
            )
            return

        try:
            dev_id_to_update = int(dev_id_to_update)
            device_data["id"] = dev_id_to_update  # Normalizar ID
        except (ValueError, TypeError):
            logger.warning(
                f"ID de dispositivo inválido '{device_data.get('id')}' en update_single_device_in_cache."
            )
            return

        for i, existing_device in enumerate(self.devices):
            if existing_device.get("id") == dev_id_to_update:
                self.devices[i] = device_data  # Reemplazar
                return
        self.devices.append(device_data)  # Añadir si no existe

    def _serialize_datetime_objects(self, obj):
        if isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize_datetime_objects(v) for k, v in obj.items()}
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    async def _load_initial_devices_cache(self):
        local_dc = DevicesController()
        try:
            all_devices = await asyncio.to_thread(local_dc.get_devices)
            await self.save_devices(all_devices)
            logger.info(
                f"Caché de dispositivos (re)cargado con {len(all_devices)} dispositivos."
            )
        except Exception as e:
            logger.error(f"Error cargando caché de dispositivos: {e}", exc_info=True)
        finally:
            if hasattr(local_dc, "close") and callable(getattr(local_dc, "close")):
                await asyncio.to_thread(local_dc.close)

    async def _update_selective_devices_cache(self):
        """
        Actualiza el caché de dispositivos de forma selectiva.

        Compara una lista fresca de dispositivos (de DevicesController) con
        el caché actual (self.devices). Actualiza solo campos
        específicos para dispositivos existentes, añade nuevos y elimina los obsoletos.
        Finalmente, guarda la lista resultante usando self.save_devices().
        """
        local_dc = DevicesController()  # Para obtener la lista fresca de dispositivos

        DEVICE_ID_FIELD = "id"  # Campo identificador único de los dispositivos.

        fields_to_update = {
            "positionid",
            "groupid",
            "attributes",
            "phone",
            "model",
            "contact",
            "category",
            "icon",
            "latitude",
            "longitude",
            "course",
            "speed",
            "driver",
            "contactos",
        }

        # Lista que contendrá el resultado final de la fusión para el caché
        merged_list_for_cache = []

        try:
            # 1. Obtener la lista "fresca" de dispositivos desde el controlador
            fresh_devices_list = await asyncio.to_thread(local_dc.get_devices)

            # 2. Obtener la lista "antigua" (caché actual)
            #    y crear un mapa para acceso rápido por ID.
            #    Accedemos a self.devices directamente como indicaste para leer el caché.
            current_cache_map = {}
            if hasattr(self, "devices") and isinstance(self.devices, list):
                for device_in_cache in self.devices:
                    device_id_val = device_in_cache.get(DEVICE_ID_FIELD)
                    if device_id_val is not None:
                        current_cache_map[device_id_val] = device_in_cache

            # 3. Procesar la lista fresca y fusionar/añadir a merged_list_for_cache
            for fresh_device in fresh_devices_list:
                fresh_device_id = fresh_device.get(DEVICE_ID_FIELD)

                if fresh_device_id is None:
                    # Dispositivo fresco sin ID, no se puede procesar. Opcionalmente loguear.
                    continue

                if fresh_device_id in current_cache_map:
                    # Dispositivo existente: tomar el del caché y actualizar campos específicos
                    cached_device = current_cache_map[fresh_device_id]

                    # Crear una copia del dispositivo cacheado para preservar sus campos no listados
                    updated_device_data = cached_device.copy()

                    # Actualizar solo los campos especificados desde el dispositivo fresco
                    for field in fields_to_update:
                        if (
                            field in fresh_device
                        ):  # Asegurarse que el campo existe en el objeto fresco
                            updated_device_data[field] = fresh_device[field]

                    merged_list_for_cache.append(updated_device_data)
                else:
                    # Dispositivo nuevo: añadirlo tal cual
                    merged_list_for_cache.append(fresh_device)

            # 4. Guardar la lista fusionada y actualizada usando el método del WsManager
            #    Esto reemplazará el caché antiguo con la nueva lista.
            if hasattr(self, "save_devices") and callable(self.save_devices):
                await self.save_devices(merged_list_for_cache)
                # logger.info(f"Caché selectivo guardado. {len(merged_list_for_cache)} dispositivos.") # Opcional
            else:
                # Fallback o error si save_devices no existe (según tu descripción, debería existir)
                logger.error(
                    "WsManager no tiene el método save_devices o no es llamable."
                )  # Opcional
                # Como alternativa, si save_devices no existiera y la única forma fuera la asignación directa:
                # self.devices = merged_list_for_cache
                # Pero sigo tu indicación de usar save_devices.
                pass

        except Exception as e:
            logger.error(
                f"Error en _update_selective_devices_cache: {e}", exc_info=True
            )  # Opcional
            # Considerar cómo manejar el error (relanzar, etc.)
            pass
        finally:
            # Asegurar que los recursos del DevicesController se liberan, si es necesario
            if hasattr(local_dc, "close") and callable(getattr(local_dc, "close")):
                await asyncio.to_thread(local_dc.close)

    async def add_vehicle_to_nearby_support_users_task(self, device: dict) -> None:
        """
        Añade asíncronamente el vehículo a usuarios de soporte cercanos (tarea "fire-and-forget").

        Consulta la API de `nearby-support` y luego asigna el vehículo a los usuarios
        mediante `UserDevicesController` (instanciado localmente). Errores se loguean.
        """
        device_id = device.get("id", None)
        latitude = device.get("latitude", None)
        longitude = device.get("longitude", None)
        category = device.get("category", "default")

        if latitude is None or longitude is None or device_id is None:
            logger.info(
                f"TASK: Datos insuficientes en 'device' (id: {device_id}, lat: {latitude}, lon: {longitude}). No se puede continuar."
            )
            return

        category_params = f"&category=salud" if category == "person" else ""
        api_url = (
            f"{API_URL_ADMIN_NWPERU}nearby-support?latitude={latitude}&longitude={longitude}"
            + category_params
        )
        user_devices_controller = UserDevicesController()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    users_data = await response.json()

                    if not users_data or not isinstance(users_data, list):
                        logger.info(
                            f"TASK: No se encontraron usuarios de soporte válidos para dispositivo {device_id} (Respuesta: {str(users_data)[:100]})."
                        )
                        return

                    tasks = []
                    for user_info in users_data:
                        if not isinstance(user_info, dict):
                            logger.warning(
                                f"TASK: Elemento de usuario no es un diccionario, se omite: {str(user_info)[:50]}"
                            )
                            continue

                        userid_val = user_info.get("userid")
                        if userid_val is None:
                            logger.warning(
                                f"TASK: Elemento de usuario sin 'userid', se omite: {user_info}"
                            )
                            continue

                        try:
                            userid = int(userid_val)
                            task = asyncio.to_thread(
                                user_devices_controller.add_user_devices,
                                userid,
                                device_id,
                            )
                            tasks.append(task)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"TASK: UserID '{userid_val}' no es un entero válido, se omite."
                            )

                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for i, res in enumerate(results):
                            if isinstance(res, Exception):
                                logger.error(
                                    f"TASK: Fallo en sub-tarea de añadir {device_id} (índice {i}): {res}"
                                )
                            elif not res:
                                logger.warning(
                                    f"TASK: Sub-tarea de añadir {device_id} (índice {i}) devolvió False."
                                )
                    else:
                        logger.info(
                            f"TASK: No se generaron tareas de adición para dispositivo {device_id}."
                        )

        except aiohttp.ClientResponseError as e_http_status:
            logger.error(
                f"TASK: Error HTTP {e_http_status.status} de API {api_url} para disp {device_id}: {e_http_status.message}",
                exc_info=False,
            )
        except aiohttp.ClientError as e_http_client:
            logger.error(
                f"TASK: Error de cliente aiohttp al contactar {api_url} para disp {device_id}: {e_http_client}",
                exc_info=False,
            )
        except (KeyError, TypeError, ValueError) as e_data:
            logger.error(
                f"TASK: Error de datos procesando para dispositivo {device_id}: {e_data}",
                exc_info=True,
            )
        except Exception as e_general:
            logger.error(
                f"TASK: Error inesperado procesando dispositivo {device_id}: {e_general}",
                exc_info=True,
            )
