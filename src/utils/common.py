import requests
import os
import json
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

URL_HOST_TRACCAR = os.getenv("URL_HOST_TRACCAR")
API_URL_TRACCAR = URL_HOST_TRACCAR + "api/"

URL_HOST_ADMIN_NWPERU = os.getenv("URL_HOST_ADMIN_NWPERU")
API_URL_ADMIN_NWPERU = URL_HOST_ADMIN_NWPERU + "api/"

HOST_URL_WHATSAPP = os.getenv("URL_HOST_API_WHATSAPP")


def login(username, password):
    # URL a la que se enviará la petición
    url = API_URL_TRACCAR + "session"
    # Datos que se enviarán en la petición
    data = {"email": username, "password": password}

    # Enviar la petición POST
    response = requests.post(url, data=data)

    # Imprimir la respuesta
    if response.status_code == 200:
        return response.json()
    else:
        return None


async def send_message_whatsapp(phone, message):
    url = HOST_URL_WHATSAPP + "send-message"
    payload = json.dumps({"number": phone, "message": message})
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("TOKEN_API_WHATSAPP"),
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)
