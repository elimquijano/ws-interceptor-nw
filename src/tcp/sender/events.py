import asyncio
import logging
from datetime import datetime
import aiohttp

from src.controllers.user_devices_controller import UserDevicesController
from src.utils.common import API_URL_ADMIN_NWPERU
from src.ws.ws_manager import WebSocketManager
from src.utils.common import send_message_whatsapp

logger = logging.getLogger(__name__)

NOTIFICATION_TEMPLATES = {
    "default": {
        "sound": "generico.wav",
        "title": "¡Alerta!",
        "channelId": "default-channel",
        "android": {
            "channelId": "default-channel",
            "vibrationPattern": [0, 250, 250, 250],
            "lightColor": "#FF231F7C",
        },
        "ios": {"sound": "generico.wav"},
    },
    "alarm": {
        "sound": "alarmanoti.wav",
        "title": "¡Alerta!",
        "channelId": "alarm-channel",
        "android": {"channelId": "alarm-channel"},
        "ios": {"sound": "alarmanoti.wav"},
    },
    "sos": {
        "sound": "sirena.wav",
        "title": "¡ALERTA DE SOS!",
        "channelId": "sos-channel",
        "android": {"channelId": "sos-channel"},
        "ios": {"sound": "sirena.wav"},
    },
}


def _build_notification_payload(
    token_value: str,
    event_type: str,
    device_name: str,
    device_id: int,
    geofence_name: str = None,
):
    base_template = NOTIFICATION_TEMPLATES.get("default", {}).copy()
    event_specific_template = NOTIFICATION_TEMPLATES.get(event_type, {}).copy()
    notification_data = {**base_template, **event_specific_template}
    if "android" in base_template and "android" in event_specific_template:
        notification_data["android"] = {
            **base_template["android"],
            **event_specific_template["android"],
        }
    if "ios" in base_template and "ios" in event_specific_template:
        notification_data["ios"] = {
            **base_template["ios"],
            **event_specific_template["ios"],
        }
    body_messages = {
        "alarm": f"Movimiento inusual en su vehiculo {device_name}",
        "sos": f"Se ha activado una alerta de SOS en su vehículo {device_name}",
        "ignitionOn": f"Encendido del vehiculo {device_name}",
        "ignitionOff": f"Apagado del vehiculo {device_name}",
        "powerCut": f"Corte de energía en su vehiculo {device_name}",
        "deviceOffline": f"El vehiculo {device_name} se encuentra desconectado",
        "deviceOverspeed": f"El vehiculo {device_name} ha excedido la velocidad permitida",
        "geofenceEnter": f"El vehiculo {device_name} ha ingresado a la geocerca {geofence_name or 'desconocida'}",
        "geofenceExit": f"El vehiculo {device_name} ha salido de la geocerca {geofence_name or 'desconocida'}",
        "lowBattery": f"Batería baja en el vehículo {device_name}",
    }
    notification_data["to"] = token_value
    notification_data["body"] = body_messages.get(
        event_type, f"Evento {event_type} en {device_name}"
    )
    notification_data["data"] = {"vehicleId": device_id, "screen": "Maps"}
    if event_type not in body_messages and event_type not in NOTIFICATION_TEMPLATES:
        return None
    return notification_data


class EventNotifierService:
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._http_session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()  # Para creación segura de sesión
        logger.info("EventNotifierService instanciado.")

    async def _get_http_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:  # Asegurar creación atómica
            if self._http_session is None or self._http_session.closed:
                self._http_session = aiohttp.ClientSession()
                logger.info("EventNotifierService: Nueva aiohttp.ClientSession creada.")
        return self._http_session

    async def close_http_session(self):
        async with self._session_lock:
            if self._http_session and not self._http_session.closed:
                await self._http_session.close()
                logger.info("EventNotifierService: aiohttp.ClientSession cerrada.")
            self._http_session = None  # Marcar como cerrada

    async def _send_expo_push(self, expo_token: str, payload: dict):
        session = await self._get_http_session()
        if not session:
            logger.error("No se pudo obtener sesión HTTP para PUSH.")
            return
        expo_url = "https://exp.host/--/api/v2/push/send"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        try:
            async with session.post(
                expo_url, headers=headers, json=payload, timeout=10
            ) as response:  # Timeout de 10s
                response_text = (
                    await response.text()
                )  # Leer siempre para liberar conexión
                if 200 <= response.status < 300:
                    # logger.debug(f"PUSH a {expo_token} OK (Status {response.status})")
                    pass
                else:
                    logger.error(
                        f"Error PUSH a Expo {expo_token} (Status {response.status}): {response_text[:500]}"
                    )
        except asyncio.TimeoutError:
            logger.error(f"Timeout enviando PUSH a Expo {expo_token}")
        except aiohttp.ClientError as e:  # Errores de conexión, etc.
            logger.error(
                f"ClientError PUSH a Expo ({expo_token}): {e}", exc_info=False
            )  # exc_info=False para no ser tan verboso
        except Exception as e:  # Otros errores inesperados
            logger.error(
                f"Error inesperado PUSH a Expo ({expo_token}): {e}", exc_info=True
            )

    async def _fetch_user_tokens_for_event(
        self, user_id: int, event_type: str
    ) -> list[str]:
        session = await self._get_http_session()
        if not session:
            logger.error("No se pudo obtener sesión HTTP para fetch_tokens.")
            return []
        url = f"{API_URL_ADMIN_NWPERU}pushtokenuser?traccar_id={user_id}&type={event_type}"
        tokens_values = []
        try:
            async with session.get(url, timeout=10) as response:  # Timeout de 10s
                if response.status == 200:
                    tokens_data = await response.json()
                    tokens_values = [
                        item.get("token") for item in tokens_data if item.get("token")
                    ]
                else:
                    logger.error(
                        f"Error obteniendo tokens PUSH para user {user_id}, event {event_type} (Status {response.status}): {await response.text()}"
                    )
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout obteniendo tokens PUSH para user {user_id}, event {event_type}"
            )
        except aiohttp.ClientError as e:
            logger.error(
                f"ClientError obteniendo tokens PUSH (user {user_id}): {e}",
                exc_info=False,
            )
        except Exception as e:
            logger.error(
                f"Excepción obteniendo tokens PUSH (user {user_id}): {e}", exc_info=True
            )
        return tokens_values

    async def _notify_single_user(
        self, user_id: int, event_data_for_notification: dict
    ):
        event_type = event_data_for_notification.get("type")
        if not event_type:
            return

        push_tokens = await self._fetch_user_tokens_for_event(user_id, event_type)
        if not push_tokens:
            return

        push_tasks = []
        for token_val in push_tokens:
            payload = _build_notification_payload(
                token_val,
                event_type,
                event_data_for_notification.get("name", "N/A"),
                event_data_for_notification.get("deviceid", 0),
                event_data_for_notification.get("geofencename"),
            )
            if payload:
                push_tasks.append(self._send_expo_push(token_val, payload))
        if push_tasks:
            await asyncio.gather(*push_tasks, return_exceptions=True)

    async def notify_event_to_users(self, users_info_list: list, event_payload: dict):
        if not users_info_list or not event_payload:
            return
        # logger.debug(f"Notificando evento {event_payload.get('type')} a {len(users_info_list)} usuarios.")
        push_notify_tasks = [
            self._notify_single_user(user_info["userid"], event_payload)
            for user_info in users_info_list
            if user_info.get("userid")
        ]
        ws_payload_wrapper = {"event": event_payload}
        ws_notify_tasks = [
            self.ws_manager.send_to_all_clients_by_userid(
                user_info["userid"], ws_payload_wrapper
            )
            for user_info in users_info_list
            if user_info.get("userid")
        ]
        await asyncio.gather(
            *push_notify_tasks, *ws_notify_tasks, return_exceptions=True
        )

    async def process_event_from_device(self, parsed_device_event: dict):
        imei = parsed_device_event.get("imei")
        event_type = parsed_device_event.get("event_type")
        if not imei or not event_type:
            return

        device_in_cache = self.ws_manager.get_device_by_uniqueid(str(imei))
        if not device_in_cache:
            logger.warning(
                f"No se encontró dispositivo para IMEI {imei} al procesar evento TCP '{event_type}'."
            )
            # Podría ser un dispositivo nuevo que aún no se ha refrescado en el caché global.
            # PositionUpdater se encarga de refrescar el caché si el IMEI es nuevo para una posición.
            # Para un evento, si el dispositivo no está, usualmente no se puede hacer mucho más.
            return

        final_event_payload = {
            "deviceid": device_in_cache["id"],
            "name": device_in_cache.get("name", "Desconocido"),
            "uniqueid": imei,
            "type": event_type,
            "eventtime": parsed_device_event.get(
                "datetime", datetime.now().isoformat()
            ),
            "latitude": parsed_device_event.get(
                "latitude", device_in_cache.get("latitude")
            ),
            "longitude": parsed_device_event.get(
                "longitude", device_in_cache.get("longitude")
            ),
        }
        if "geofencename" in parsed_device_event:
            final_event_payload["geofencename"] = parsed_device_event["geofencename"]

        # Usar instancia local de UserDevicesController para esta operación
        ud_controller_local = UserDevicesController()
        try:
            associated_users = await asyncio.to_thread(
                ud_controller_local.get_users, device_in_cache["id"]
            )
        except Exception as e:
            logger.error(
                f"Error obteniendo usuarios para device_id {device_in_cache['id']} (evento {event_type}): {e}",
                exc_info=True,
            )
            return
        finally:
            await asyncio.to_thread(ud_controller_local.close)  # Cerrar conexión local

        if associated_users:
            await self.notify_event_to_users(associated_users, final_event_payload)

        # enviar a whatsapp si son eventos de tipo powerCut y lowBattery
        if event_type in ["powerCut", "lowBattery"]:
            device_name = device_in_cache.get("name", "Desconocido")
            message = (
                f"Corte de energía en su vehiculo {device_name}"
                if event_type == "powerCut"
                else f"Batería baja en su vehiculo {device_name}"
            )
            for number in device_in_cache.get("contactos", []):
                number_phone = "51" + number
                logger.info(f"Enviando mensaje a {number_phone}: {message}")
                asyncio.create_task(send_message_whatsapp(number_phone, message))

    async def create_and_notify_custom_event(
        self, device_info: dict, event_type: str, additional_data: dict = None
    ):
        if not device_info or not device_info.get("id"):
            return

        event_payload = {
            "deviceid": device_info["id"],
            "name": device_info.get("name", "Desconocido"),
            "uniqueid": device_info.get("uniqueid"),
            "type": event_type,
            "eventtime": datetime.now().isoformat(),
            "latitude": device_info.get("latitude"),
            "longitude": device_info.get("longitude"),
        }
        if additional_data:
            event_payload.update(additional_data)

        ud_controller_local = UserDevicesController()
        try:
            associated_users = await asyncio.to_thread(
                ud_controller_local.get_users, device_info["id"]
            )
        except Exception as e:
            logger.error(
                f"Error obteniendo usuarios para evento custom '{event_type}', device_id {device_info['id']}: {e}",
                exc_info=True,
            )
            return
        finally:
            await asyncio.to_thread(ud_controller_local.close)

        if associated_users:
            await self.notify_event_to_users(associated_users, event_payload)

        # enviar a whatsapp si son eventos de tipo powerCut y lowBattery
        if event_type in ["sos", "geofenceEnter", "geofenceExit"]:
            device_name = device_info.get("name", "Desconocido")
            message = (
                f"SOS activado en su vehiculo {device_name}"
                if event_type == "sos"
                else (
                    f"Su vehiculo {device_name} salió de la GeoCerca {additional_data.get('geofencename', 'Desconocido')}"
                    if event_type == "geofenceEnter"
                    else f"Su vehiculo {device_name} ingresó a la GeoCerca {additional_data.get('geofencename', 'Desconocido')}"
                )
            )
            for number in device_info.get("contactos", []):
                number_phone = "51" + number
                logger.info(f"Enviando mensaje a {number_phone}: {message}")
                asyncio.create_task(send_message_whatsapp(number_phone, message))
