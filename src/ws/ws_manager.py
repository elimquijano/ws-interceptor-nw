import json
import asyncio
from datetime import datetime
import logging

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
