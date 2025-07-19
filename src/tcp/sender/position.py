import asyncio
import logging
from datetime import datetime
from src.controllers.device_geofence_controller import (
    DeviceGeofenceController,
)
from src.utils.geofence import check_geofence_event
from src.ws.ws_manager import WebSocketManager
from src.controllers.devices_controller import (
    DevicesController,
)
from src.tcp.sender.events import EventNotifierService
from src.utils.common import get_datetime_now

logger = logging.getLogger(__name__)


def is_more_recent_gps_date(prev_dt_str: str | None, curr_dt_str: str) -> bool:
    if not prev_dt_str:
        return True
    try:
        return datetime.strptime(prev_dt_str, "%Y-%m-%d %H:%M:%S") < datetime.strptime(
            curr_dt_str, "%Y-%m-%d %H:%M:%S"
        )
    except ValueError:
        logger.warning(f"Error comparando fechas: '{prev_dt_str}' vs '{curr_dt_str}'")
        return False


class PositionUpdater:
    def __init__(
        self, ws_manager: WebSocketManager, event_notifier: EventNotifierService
    ):
        self.ws_manager = ws_manager
        self.event_notifier = event_notifier
        self.devices_controller_internal = DevicesController()
        self._refresh_lock = (
            asyncio.Lock()
        )
        logger.info("PositionUpdater instanciado.")

    async def _close_internal_controllers(self):
        """Cierra los controladores que esta instancia de PositionUpdater gestiona."""
        if hasattr(self.devices_controller_internal, "close") and callable(
            getattr(self.devices_controller_internal, "close")
        ):
            await asyncio.to_thread(self.devices_controller_internal.close)
            logger.info("DevicesController interno de PositionUpdater cerrado.")

    async def process_position_update(self, position_event_data: dict):
        imei = position_event_data.get("imei")
        new_dt_str = position_event_data.get("datetime")
        if not imei or not new_dt_str:
            return

        device_in_cache = self.ws_manager.get_device_by_uniqueid(str(imei))

        if not device_in_cache:
            logger.info(
                f"IMEI {imei} no encontrado en caché. Disparando refresco completo desde API."
            )
            await self.ws_manager._update_selective_devices_cache()
            device_in_cache = self.ws_manager.get_device_by_uniqueid(
                str(imei)
            )
            if not device_in_cache:
                logger.warning(
                    f"Posición IMEI {imei}: dispositivo aún no encontrado en caché después de refresco completo desde API."
                )
                return

        prev_geo = {
            "id": device_in_cache["id"],
            "name": device_in_cache.get("name"),
            "uniqueid": device_in_cache["uniqueid"],
            "latitude": device_in_cache.get("latitude"),
            "longitude": device_in_cache.get("longitude"),
            "lastupdate": device_in_cache.get("lastupdate"),
            "contactos": device_in_cache.get("contactos"),
        }

        if not is_more_recent_gps_date(prev_geo["lastupdate"], new_dt_str):
            return

        laststop_val = device_in_cache.get(
            "laststop", get_datetime_now()
        )

        device_in_cache["latitude"] = position_event_data.get("latitude", 0.0)
        device_in_cache["longitude"] = position_event_data.get("longitude", 0.0)
        current_speed = position_event_data.get("speed", 0.0)
        device_in_cache["speed"] = current_speed
        device_in_cache["course"] = position_event_data.get("course", 0.0)
        device_in_cache["lastupdate"] = new_dt_str
        device_in_cache["status"] = "online"
        device_in_cache["laststop"] = (
            laststop_val if current_speed == 0.0 else new_dt_str
        )

        await self._check_geofence_transitions(prev_geo, position_event_data)

    async def _check_geofence_transitions(
        self, prev_dev_state: dict, curr_pos_data: dict
    ):
        dev_id = prev_dev_state.get("id")
        if dev_id is None:
            return

        local_dgc = DeviceGeofenceController()
        try:
            geofences = await asyncio.to_thread(local_dgc.get_geofences, dev_id)
            if not geofences:
                return

            curr_pt = {
                "latitude": curr_pos_data["latitude"],
                "longitude": curr_pos_data["longitude"],
            }
            prev_pt = {
                "latitude": prev_dev_state["latitude"],
                "longitude": prev_dev_state["longitude"],
            }
            if prev_pt["latitude"] is None or prev_pt["longitude"] is None:
                return

            for gf in geofences:
                if not gf.get("area"):
                    continue
                trans_type = check_geofence_event(gf["area"], prev_pt, curr_pt)
                if trans_type:
                    await self.event_notifier.create_and_notify_custom_event(
                        device_info=prev_dev_state,
                        event_type=trans_type,
                        additional_data={"geofencename": gf.get("name", "N/A")},
                    )
        except Exception as e:
            logger.error(
                f"Error procesando geocercas para device_id {dev_id}: {e}",
                exc_info=False,
            )  # Menos verboso
        finally:
            if hasattr(local_dgc, "close") and callable(getattr(local_dgc, "close")):
                await asyncio.to_thread(
                    local_dgc.close
                )  # Cerrar instancia local de DGC

    async def update_device_last_seen(self, conn_event_data: dict):
        imei = conn_event_data.get("imei")
        conn_dt = conn_event_data.get("datetime")
        if not imei or not conn_dt:
            return

        dev_cache = self.ws_manager.get_device_by_uniqueid(str(imei))
        if not dev_cache:
            logger.info(
                f"Conexión de IMEI {imei} no encontrado en caché. Disparando refresco completo desde API."
            )
            await self.ws_manager._update_selective_devices_cache() 
            dev_cache = self.ws_manager.get_device_by_uniqueid(str(imei))
            if not dev_cache:
                logger.warning(
                    f"Conexión IMEI {imei}: dispositivo aún no encontrado en caché después de refresco completo desde API."
                )
                return

        if is_more_recent_gps_date(dev_cache.get("lastupdate"), conn_dt):
            dev_cache["lastupdate"] = conn_dt
            dev_cache["status"] = "online"
