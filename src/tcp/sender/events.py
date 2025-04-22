import json
import requests
import asyncio
from src.controllers.user_devices_controller import UserDevicesController
from src.utils.common import API_URL_ADMIN_NWPERU
from src.ws.ws_manager import WebSocketManager
from datetime import datetime


class Events:
    def __init__(self):
        self.ws_manager = WebSocketManager()

    async def send_events_to_users(self, port, event):
        devices = self.ws_manager.devices
        if event["type"] == "event":
            found_device = next(
                (device for device in devices if device["uniqueid"] == event["imei"]), None
            )
            if found_device:
                ud_controller = UserDevicesController()
                users = ud_controller.get_users(found_device["id"])
                process_data = {
                    "deviceid": found_device["id"],
                    "name": found_device["name"],
                    "uniqueid": event["imei"],
                    "type": event["event_type"],
                    "eventtime": event["datetime"],
                    "latitude": found_device["latitude"],
                    "longitude": found_device["longitude"],
                }
                asyncio.create_task(send_notificacion(users, process_data))
                asyncio.create_task(self.ws_manager.send_events(users, process_data))
                # print(f"Event created")

    async def create_sos_event(self, device):
        # Buscar usuarios asociados al dispositivo
        ud_controller = UserDevicesController()
        users = ud_controller.get_users(device["id"])
        sos_data = {
            "deviceid": device["id"],
            "name": device["name"],
            "uniqueid": device["uniqueid"],
            "type": "sos",
            "eventtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": device["latitude"],
            "longitude": device["longitude"],
        }

        asyncio.create_task(send_notificacion(users, sos_data))
        asyncio.create_task(self.ws_manager.send_events(users, sos_data))
        # print("SOS event created")


async def send_push_notification(token, event):
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
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"Encendido del vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    elif event["type"] == "ignitionOff":
        data = {
            "to": token["token"],
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"Apagado del vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    elif event["type"] == "powerCut":
        data = {
            "to": token["token"],
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"Corte de energía en su vehiculo {event['name']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    elif event["type"] == "deviceOverspeed":
        data = {
            "to": token["token"],
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"El vehiculo {event['name']} ha excedido la velocidad permitida",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    elif event["type"] == "geofenceEnter":
        data = {
            "to": token["token"],
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"El vehiculo {event['name']} ha ingresado a la geocerca {event['geofencename']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    elif event["type"] == "geofenceExit":
        data = {
            "to": token["token"],
            "sound": "generico.wav",
            "title": "¡Alerta!",
            "body": f"El vehiculo {event['name']} ha salido de la geocerca {event['geofencename']}",
            "data": {
                "vehicleId": event["deviceid"],
                "screen": "Maps",
            },
            "channelId": "default-channel",
            "android": {
                "channelId": "default-channel",
                "vibrationPattern": [0, 250, 250, 250],
                "lightColor": "#FF231F7C",
            },
            "ios": {
                "sound": "generico.wav",
            },
        }
    else:
        data = None

    if data is not None:
        # Realiza la solicitud POST
        try:
            print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Enviar notificacion a token {token['token']}")
            response = requests.post(url, headers=headers, data=json.dumps(data))
            # Muestra el estado de la respuesta
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), {"status": response.status_code, "message": response.json()})

        except requests.exceptions.RequestException as e:
            print(f"Ocurrió un error al realizar la solicitud: {e}")


async def get_tokens_and_send_notification(userid, event):
    try:
        # buscar tokens por cada usuario
        url = f"{API_URL_ADMIN_NWPERU}pushtokenuser?traccar_id={userid}&type={event['type']}"
        response = requests.get(url)
        if response.status_code == 200:
            tokens = response.json()
            print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Enviar notificacion a tokens")
            for token in tokens:
                # enviar notificacion a cada token
                asyncio.create_task(send_push_notification(token, event))
    except Exception as e:
        print(f"Error al enviar notificacion: {e}")


async def send_notificacion(users, event):
    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Enviar notificacion a usuarios")
    for user in users:
        asyncio.create_task(get_tokens_and_send_notification(user["userid"], event))

