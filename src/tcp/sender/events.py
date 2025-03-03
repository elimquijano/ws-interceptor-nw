import json
import requests
import asyncio
from datetime import datetime
from src.controllers.user_devices_controller import UserDevicesController
from src.utils.common import API_URL_ADMIN_NWPERU


async def send_push_notification(token, event):
    print(token, event)
    # URL de la API de Expo para enviar notificaciones
    url = "https://exp.host/--/api/v2/push/send"
    # Encabezados de la solicitud
    headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
    # Datos de la notificación
    
    if event["type"] == "alarm":
        data = {
            "to": token["token"],
            "sound": "alarmanoti.wav",
            "title": "¡Alerta!",
            "body": f"Movimiento inusual en su vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "alarm-channel",
            "android": {
                "channelId": "alarm-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "alarmanoti.wav",
            },
        }
    elif event["type"] == "sos":
        data = {
            "to": token["token"],
            "sound": "sirena.wav",
            "title": "¡ALERTA DE SOS!",
            "body": f"Se ha activado una alerta de SOS en su vehículo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "sos-channel",
            "android": {
                "channelId": "sos-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "sirena.wav",
            },
        }
    elif event["type"] == "ignitionOn":
        data = {
            "to": token["token"],
            "title": "¡Alerta!",
            "body": f"Encendido del vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "android": {
                "vibrationPattern": [0, 250, 250, 250],
            }
        }
    elif event["type"] == "ignitionOff":
        data = {
            "to": token["token"],
            "title": "¡Alerta!",
            "body": f"Apagado del vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "android": {
                "vibrationPattern": [0, 250, 250, 250],
            }
        }
    elif event["type"] == "powerCut":
        data = {
            "to": token["token"],
            "title": "¡Alerta!",
            "body": f"Corte de energía en su vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "android": {
                "vibrationPattern": [0, 250, 250, 250],
            }
        }
    else:
        data = None

    if data is not None:
        # Realiza la solicitud POST
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            # Muestra el estado de la respuesta
            print(f"Estado: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Ocurrió un error al realizar la solicitud: {e}")


async def get_tokens_and_send_notification(userid, event):
    try:
        # buscar tokens por cada usuario
        url = f"{API_URL_ADMIN_NWPERU}pushtokenuser?traccar_id={userid}"
        response = requests.get(url)
        if response.status_code == 200:
            tokens = response.json()
            print(f"Tokens: {tokens}")
            for token in tokens:
                # enviar notificacion a cada token
                asyncio.create_task(send_push_notification(token, event))
    except Exception as e:
        print(f"Error al enviar notificacion: {e}")


async def send_notificacion(users, event):
    for user in users:
        asyncio.create_task(get_tokens_and_send_notification(user["userid"], event))


async def get_users_and_process_data(port, event, devices):
    if event["type"] == "event":
        data = event["data"]
        print(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando busqueda del vehiculo"
        )
        found_device = next(
            (device for device in devices if device["uniqueid"] == data["imei"]), None
        )
        if found_device:
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Vehiculo encontrado"
            )
            ud_controller = UserDevicesController()
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando busqueda de usuarios"
            )
            users = ud_controller.get_users(found_device["id"])
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Usuarios encontrados"
            )
            process_data = {
                "deviceid": found_device["id"],
                "name": found_device["name"],
                "uniqueid": data["imei"],
                "type": data["event_type"],
                "eventtime": data["datetime"],
                "latitude": data["latitude"],
                "longitude": data["longitude"],
            }
            result = {"users": users, "process_data": process_data}
            return result
        return None
    else:
        return None
