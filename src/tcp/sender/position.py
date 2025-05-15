import asyncio
import logging
from datetime import datetime
from src.controllers.device_geofence_controller import DeviceGeofenceController
from src.utils.geofence import check_geofence_event
from src.ws.ws_manager import WebSocketManager
from src.controllers.devices_controller import DevicesController
from src.tcp.sender.events import EventNotifierService

logger = logging.getLogger(__name__)


def is_more_recent_gps_date(
    previous_datetime_str: str | None, current_datetime_str: str
) -> bool:
    if not previous_datetime_str:
        return True
    try:
        prev_dt = datetime.strptime(previous_datetime_str, "%Y-%m-%d %H:%M:%S")
        curr_dt = datetime.strptime(current_datetime_str, "%Y-%m-%d %H:%M:%S")
        return curr_dt > prev_dt
    except ValueError:
        logger.warning(
            f"Error comparando fechas GPS: '{previous_datetime_str}' vs '{current_datetime_str}'"
        )
        return False


class PositionUpdater:
    def __init__(
        self, ws_manager: WebSocketManager, event_notifier: EventNotifierService
    ):
        self.ws_manager = ws_manager
        self.event_notifier = event_notifier
        self.device_controller = (
            DevicesController()
        )  # Instancia para uso interno de PositionUpdater
        self._refresh_lock = (
            asyncio.Lock()
        )  # Para evitar refrescos concurrentes del caché completo
        logger.info("PositionUpdater instanciado.")

    async def _close_internal_controllers(self):
        """Cierra controladores internos si es necesario."""
        if hasattr(self.device_controller, "close") and callable(
            getattr(self.device_controller, "close")
        ):
            await asyncio.to_thread(self.device_controller.close)
            logger.info("DevicesController de PositionUpdater cerrado.")

    async def _refresh_full_devices_cache_if_needed(self):
        """Refresca el caché global de dispositivos si un IMEI es desconocido."""
        async with self._refresh_lock:  # Solo un refresco a la vez
            logger.info(
                "Iniciando refresco completo del caché de dispositivos desde PositionUpdater..."
            )
            try:
                all_devices_from_db = await asyncio.to_thread(
                    self.device_controller.get_devices
                )
                await self.ws_manager.save_devices(
                    all_devices_from_db
                )  # Usa el método correcto
                logger.info(
                    f"Caché de dispositivos refrescado con {len(all_devices_from_db)} dispositivos."
                )
            except Exception as e:
                logger.error(
                    f"Error durante el refresco completo del caché: {e}", exc_info=True
                )

    async def process_position_update(self, position_event_data: dict):
        imei = position_event_data.get("imei")
        new_datetime_str = position_event_data.get("datetime")
        if not imei or not new_datetime_str:
            return

        device_in_cache = self.ws_manager.get_device_by_uniqueid(str(imei))

        if not device_in_cache:
            await self._refresh_full_devices_cache_if_needed()  # Refresca si no está
            device_in_cache = self.ws_manager.get_device_by_uniqueid(
                str(imei)
            )  # Intenta de nuevo
            if not device_in_cache:
                logger.warning(
                    f"Posición IMEI {imei}: dispositivo no encontrado tras refresco."
                )
                return

        if not is_more_recent_gps_date(
            device_in_cache.get("lastupdate"), new_datetime_str
        ):
            return

        previous_geo_state = {
            "id": device_in_cache["id"],
            "name": device_in_cache.get("name"),
            "uniqueid": device_in_cache["uniqueid"],
            "latitude": device_in_cache.get("latitude"),
            "longitude": device_in_cache.get("longitude"),
        }

        # Tu lógica para laststop
        laststop_to_use_if_stopped = device_in_cache.get(
            "laststop", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Actualizar datos del dispositivo en el caché (el objeto es modificado por referencia)
        device_in_cache["latitude"] = position_event_data.get("latitude", 0.0)
        device_in_cache["longitude"] = position_event_data.get("longitude", 0.0)
        current_speed = position_event_data.get("speed", 0.0)
        device_in_cache["speed"] = current_speed
        device_in_cache["course"] = position_event_data.get("course", 0.0)
        device_in_cache["lastupdate"] = new_datetime_str
        device_in_cache["status"] = "online"
        device_in_cache["laststop"] = (
            laststop_to_use_if_stopped if current_speed == 0.0 else new_datetime_str
        )

        await self._check_geofence_transitions(previous_geo_state, position_event_data)

    async def _check_geofence_transitions(
        self, previous_device_state: dict, current_position_data: dict
    ):
        device_id = previous_device_state.get("id")
        if device_id is None:
            return

        dg_controller_local = DeviceGeofenceController()  # Instancia local
        try:
            geofences_for_device = await asyncio.to_thread(
                dg_controller_local.get_geofences, device_id
            )
            if not geofences_for_device:
                return

            current_geo_point = {
                "latitude": current_position_data["latitude"],
                "longitude": current_position_data["longitude"],
            }
            previous_geo_point = {
                "latitude": previous_device_state["latitude"],
                "longitude": previous_device_state["longitude"],
            }
            if (
                previous_geo_point["latitude"] is None
                or previous_geo_point["longitude"] is None
            ):
                return

            for geofence in geofences_for_device:
                geofence_area = geofence.get("area")
                if not geofence_area:
                    continue
                transition_type = check_geofence_event(
                    geofence_area, previous_geo_point, current_geo_point
                )
                if transition_type:
                    await self.event_notifier.create_and_notify_custom_event(
                        device_info=previous_device_state,
                        event_type=transition_type,
                        additional_data={"geofencename": geofence.get("name", "N/A")},
                    )
        except Exception as e:
            logger.error(
                f"Error obteniendo/procesando geocercas para device_id {device_id}: {e}",
                exc_info=True,
            )
        finally:
            if hasattr(dg_controller_local, "close") and callable(
                getattr(dg_controller_local, "close")
            ):
                await asyncio.to_thread(
                    dg_controller_local.close
                )  # Cerrar instancia local

    async def update_device_last_seen(self, connection_event_data: dict):
        imei = connection_event_data.get("imei")
        conn_dt_str = connection_event_data.get("datetime")
        if not imei or not conn_dt_str:
            return

        device_in_cache = self.ws_manager.get_device_by_uniqueid(str(imei))
        if not device_in_cache:
            await self._refresh_full_devices_cache_if_needed()
            device_in_cache = self.ws_manager.get_device_by_uniqueid(str(imei))
            if not device_in_cache:
                logger.warning(
                    f"Conexión IMEI {imei}: dispositivo no encontrado tras refresco."
                )
                return

        if is_more_recent_gps_date(device_in_cache.get("lastupdate"), conn_dt_str):
            device_in_cache["lastupdate"] = conn_dt_str
            device_in_cache["status"] = "online"
