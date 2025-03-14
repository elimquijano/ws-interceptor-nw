import asyncio
from datetime import datetime, timedelta
from src.controllers.device_geofence_controller import DeviceGeofenceController
from src.utils.geofence import check_geofence_event
from src.ws.ws_manager import WebSocketManager
from src.controllers.user_devices_controller import UserDevicesController
from src.controllers.devices_controller import DevicesController
from src.tcp.sender.events import send_notificacion


class Position:
    def __init__(self):
        self.ws_manager = WebSocketManager()

    async def update_position(self, port, event):
        devices = self.ws_manager.devices
        for device in devices:
            if device["uniqueid"] == event["imei"] and es_fecha_mas_reciente(
                device["lastupdate"], event["datetime"]
            ):
                print(f"Posicion aceptada para {device['name']}")
                # Create a copy of the original device state before modifying it
                device_copy = {
                    "id": device["id"],
                    "name": device["name"],
                    "uniqueid": device["uniqueid"],
                    "latitude": device["latitude"],
                    "longitude": device["longitude"],
                }

                # Create the task with the copy
                asyncio.create_task(self.check_geofence(device_copy, event))

                # Now update the original device
                device["latitude"] = event.get("latitude", 0.0)
                device["longitude"] = event.get("longitude", 0.0)
                device["speed"] = event.get("speed", 0.0)
                device["lastupdate"] = event["datetime"]
                device["course"] = event.get("course", 0.0)
                device["status"] = "online"

                break
        await self.ws_manager.save_devices(devices)

    async def check_geofence(self, device, event):
        dg_controller = DeviceGeofenceController()
        geofences = dg_controller.get_geofences(device["id"])

        for geofence in geofences:
            prev_position = {
                "latitude": device["latitude"],
                "longitude": device["longitude"],
            }
            current_position = {
                "latitude": event["latitude"],
                "longitude": event["longitude"],
            }

            geofence_event = check_geofence_event(
                geofence["area"], prev_position, current_position
            )

            if geofence_event is not None:
                geofence_data = {
                    "deviceid": device["id"],
                    "name": device["name"],
                    "uniqueid": device["uniqueid"],
                    "type": geofence_event,
                    "eventtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "latitude": event["latitude"],
                    "longitude": event["longitude"],
                    "geofencename": geofence["name"],
                }
                # Buscar usuarios asociados al dispositivo
                ud_controller = UserDevicesController()
                users = ud_controller.get_users(device["id"])
                asyncio.create_task(send_notificacion(users, geofence_data))
                asyncio.create_task(self.ws_manager.send_events(users, geofence_data))
                print("Geofence event")

    async def update_lastupdate(self, port, event):
        devices = self.ws_manager.devices
        found_device = next(
            (device for device in devices if device["uniqueid"] == event["imei"]), None
        )
        if not found_device:
            # Es un vehiculo nuevo, se debe agregar a la lista de dispositivos
            device_controller = DevicesController()
            devices = device_controller.get_devices()
            await self.ws_manager.save_devices(devices)
            devices = self.ws_manager.devices

        for device in devices:
            if device["uniqueid"] == event["imei"]:
                device["lastupdate"] = event["datetime"]
                device["status"] = "online"
                break
        await self.ws_manager.save_devices(devices)


def es_fecha_mas_reciente(fecha_anterior_str, fecha_actual_str):
    # Convertir las cadenas a objetos datetime
    fecha_anterior = datetime.strptime(fecha_anterior_str, "%Y-%m-%d %H:%M:%S")
    fecha_actual = datetime.strptime(fecha_actual_str, "%Y-%m-%d %H:%M:%S")

    # Comparar las fechas
    return fecha_actual > fecha_anterior


def five_hours_ago(datetime_str):
    # Convertir la cadena de fecha y hora del vehículo a un objeto datetime
    vehicle_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    # Restar 5 horas a la fecha y hora del vehículo
    five_hours_ago_datetime = vehicle_datetime - timedelta(hours=5)
    # Devolver la fecha y hora resultante en formato de cadena
    return five_hours_ago_datetime.strftime("%Y-%m-%d %H:%M:%S")
