import requests
import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

URL_HOST_TRACCAR = os.getenv("URL_HOST_TRACCAR")
API_URL_TRACCAR = URL_HOST_TRACCAR + "api/"

URL_HOST_ADMIN_NWPERU = os.getenv("URL_HOST_ADMIN_NWPERU")
API_URL_ADMIN_NWPERU = URL_HOST_ADMIN_NWPERU + "api/"


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
