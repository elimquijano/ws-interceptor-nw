import json
import requests
import base64
from urllib.parse import urlparse, parse_qs
from datetime import datetime

clients = {}

async def authenticate_client(websocket, path):
    query_params = parse_qs(urlparse(path).query)
    username = query_params.get("u", [None])[0]
    password = query_params.get("p", [None])[0]
    
    print(f"Connection request from {username} with password {password}")

    if not username or not password:
        await websocket.close()
        print("Connection rejected: Authentication required")
        return None

    devices = login(username, password)
    if not devices:
        await websocket.close()
        print("Connection rejected: Invalid credentials")
        return None

    return devices

def login(username, password):
    # Codificar las credenciales en Base64
    token = base64.b64encode(f"{username}:{password}".encode()).decode()

    # Realizar la solicitud GET
    headers = {
        "Authorization": f"Basic {token}",
    }

    response = requests.get("http://200.234.225.210:8082/api/devices", headers=headers)

    # Verificar si la respuesta es exitosa
    if response.ok:
        data = response.json()
        return data
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

async def broadcast(unique_id, type, message_data):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Broadcasting message to {unique_id} of type {type}")
    for client_id, client_info in clients.items():
        devices = client_info["devices"]
        for device in devices:
            if device["uniqueId"] == unique_id:
                websocket = client_info["websocket"]
                # Convertir el mensaje a JSON antes de enviarlo
                await websocket.send(json.dumps({"type": type, "data": message_data}))
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                print(f"Sent message to client {client_id}")
