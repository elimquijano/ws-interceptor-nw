import socket
import json
import threading
import asyncio
from datetime import datetime, timedelta
from .utils import broadcast


def sinotrack_position_json(parts):
    # Extraer y convertir los campos necesarios
    protocol = "h02"
    device_imei = parts[1].strip()

    # Convertir la hora y fecha
    device_time = datetime.strptime(parts[3] + parts[11], "%H%M%S%d%m%y")
    server_time = device_time + timedelta(seconds=4)

    # Convertir latitud y longitud
    latitude = float(parts[5][:2]) + float(parts[5][2:]) / 60
    if parts[6] == "S":
        latitude = -latitude

    longitude = float(parts[7][:3]) + float(parts[7][3:]) / 60
    if parts[8] == "W":
        longitude = -longitude

    # Extraer otros campos
    valid = "1" if parts[4] == "A" else "0"
    altitude = float(parts[13])
    speed = float(parts[9])
    course = float(parts[10])

    # Crear el diccionario con los campos especificados
    result = {
        "protocol": protocol,
        "uniqueId": device_imei,
        "servertime": server_time.strftime("%Y-%m-%d %H:%M:%S"),
        "devicetime": device_time.strftime("%Y-%m-%d %H:%M:%S"),
        "fixtime": device_time.strftime("%Y-%m-%d %H:%M:%S"),
        "valid": valid,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "speed": speed,
        "course": course,
    }

    # Convertir el diccionario a JSON
    json_result = json.dumps(result, indent=4)
    return json_result


def tcp_to_json(port, data):
    if port == 6001:
        return data
    elif port == 6013:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"Received data from TCP port {port}: {data}")
        parts = data.split(",")
        if parts[0] == "*HQ":
            type = "position"
            data_json = json.loads(sinotrack_position_json(parts))
            asyncio.run(broadcast(data_json["uniqueId"], type, data_json))


def handle_tcp_client(conn, addr):
    print(f"Connection established by {addr}")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        try:
            received_json = json.loads(data.decode("utf-8"))
            port = received_json["port"]
            message_data = received_json["data"]
            tcp_to_json(port, message_data)
        except json.JSONDecodeError as e:
            print(f"Receiver: Invalid JSON received: {e}")
            print(f"Receiver: Raw data received: {data.decode('utf-8')}")
        except KeyError as e:
            print(f"Receiver: Missing key in JSON: {e}")
    conn.close()


def start_tcp_server(port=7005):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", port))
    s.listen(5)
    print(f"TCP server listening on port {port}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_tcp_client, args=(conn, addr)).start()
