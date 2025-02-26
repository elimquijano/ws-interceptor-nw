import requests

URL_HOST_TRACCAR = "http://200.234.225.210:8082/"
API_URL_TRACCAR = URL_HOST_TRACCAR + "api/"


def login(username, password):
    # URL a la que se enviará la petición
    url = API_URL_TRACCAR + "session"
    # Datos que se enviarán en la petición
    data = {"email": username, "password": password}

    # Enviar la petición POST
    response = requests.post(url, data=data)

    # Imprimir la respuesta
    if response.status_code == 200:
        print("Código de estado:", response.status_code)
        print("Respuesta del servidor:", response.text)
        return response.text
    else:
        return None
