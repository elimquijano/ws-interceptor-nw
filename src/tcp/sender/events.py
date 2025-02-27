from src.controllers.user_devices_controller import UserDevicesController
import requests
from datetime import datetime
import json


async def send_push_notificacion(users, data):
    for user in users:
        # buscar tokens por cada usuario
        # enviar notificacion a cada token
        pass


async def send_event(event, devices):
    if event["type"] == "event":
        data = event["data"]
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando busqueda del vehiculo")
        found_device = next(
            (device for device in devices if device["uniqueid"] == data["imei"]), None
        )
        if found_device:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Vehiculo encontrado")
            ud_controller = UserDevicesController()
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando busqueda de usuarios")
            users = ud_controller.get_users(found_device["id"])
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Usuarios encontrados")
            process_data = {
                "deviceid": found_device["id"],
                "name": found_device["name"],
                "uniqueid": data["imei"],
                "type": data["event_type"],
                "eventtime": data["datetime"],
                "latitude": data["latitude"],
                "longitude": data["longitude"],
            }
            await send_push_notificacion(users, process_data)
            return users, process_data
        return None
    else:
        return None
