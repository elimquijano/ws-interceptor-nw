import socket
import json
import threading
import asyncio
from datetime import datetime, timedelta
from .utils import broadcast


def parse_raw_data(raw_data):
    # Dividir el string en partes
    parts = raw_data.split(',')

    # Inicializar un diccionario para almacenar la información
    data = {}

    # Determinar el tipo de evento
    if parts[2] == 'V1':
        data['type'] = 'real-time location'
    elif parts[2] == 'XT':
        data['type'] = 'heartbeat packet'
    elif parts[2] == 'VI1':
        data['type'] = 'location request'
    elif parts[2] == 'BC':
        data['type'] = 'blind spots uploading'
    elif parts[2] == 'ALRM':
        data['type'] = 'device alarm'
    elif parts[2] == 'S20':
        data['type'] = 'cut-off oil & engine/recovery oil & engine'
    elif parts[2] == 'CR':
        data['type'] = 'response to location request'
    elif parts[2] == 'SF':
        data['type'] = 'fortification'
    elif parts[2] == 'SF2':
        data['type'] = 'fortification version II'
    elif parts[2] == 'CF':
        data['type'] = 'disarming'
    elif parts[2] == 'CF2':
        data['type'] = 'disarming version II'
    elif parts[2] == 'UR':
        data['type'] = 'main number bind'
    elif parts[2] == 'IP':
        data['type'] = 'server setting'
    elif parts[2] == 'MP':
        data['type'] = 'terminal password setting'
    elif parts[2] == 'XT/NXT':
        data['type'] = 'interval setting'
    elif parts[2] == 'KC':
        data['type'] = 'alarm setting'
    elif parts[2] == 'CQ':
        data['type'] = 'device reboot'
    elif parts[2] == 'RESET':
        data['type'] = 'reset to defaults'
    elif parts[2] == 'APN':
        data['type'] = 'network access point'
    elif parts[2] == 'ACPC':
        data['type'] = 'answer mode'
    elif parts[2] == 'SIMEI':
        data['type'] = 'IMEI setting'
    elif parts[2] == 'SLAN':
        data['type'] = 'language setting'
    elif parts[2] == 'CALB':
        data['type'] = 'audio monitor'
    elif parts[2] == 'PWM':
        data['type'] = 'power saving mode setting'
    elif parts[2] == 'INFO':
        data['type'] = 'query device information'
    else:
        data['type'] = 'unknown'

    # Extraer los datos según el tipo de evento
    if data['type'] in ['real-time location', 'location request', 'blind spots uploading', 'device alarm']:
        data['data'] = {
            'terminal_no': parts[1],
            'time': parts[3],
            'data_valid_bit': parts[4],
            'latitude': parts[5],
            'latitude_symbol': parts[6],
            'longitude': parts[7],
            'longitude_symbol': parts[8],
            'speed': parts[9],
            'direction': parts[10],
            'date': parts[11],
            'vehicle_status': parts[12],
            'power_capacity': parts[13],
            'mcc': parts[14],
            'mnc': parts[15],
            'lac1': parts[16],
            'cid1': parts[17],
            'lac2': parts[18],
            'cid2': parts[19],
            'lac3': parts[20],
            'cid3': parts[21]
        }
    elif data['type'] == 'heartbeat packet':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'cut-off oil & engine/recovery oil & engine':
        data['data'] = {
            'terminal_no': parts[1],
            'time': parts[3],
            'ultimate_power_mode': parts[4],
            'cut_off_or_recovery': parts[5]
        }
    elif data['type'] == 'response to location request':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'fortification' or data['type'] == 'fortification version II':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'disarming' or data['type'] == 'disarming version II':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'main number bind':
        data['data'] = {
            'terminal_no': parts[1],
            'num_list': parts[3]
        }
    elif data['type'] == 'server setting':
        data['data'] = {
            'terminal_no': parts[1],
            'index': parts[3],
            'ip': parts[4],
            'port': parts[5],
            'domain': parts[6],
            'time': parts[7]
        }
    elif data['type'] == 'terminal password setting':
        data['data'] = {
            'terminal_no': parts[1],
            'old_password': parts[3],
            'new_password': parts[4]
        }
    elif data['type'] == 'interval setting':
        data['data'] = {
            'terminal_no': parts[1],
            'interval': parts[3]
        }
    elif data['type'] == 'alarm setting':
        data['data'] = {
            'terminal_no': parts[1],
            'key': parts[3],
            'type': parts[4]
        }
    elif data['type'] == 'device reboot':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'reset to defaults':
        data['data'] = {
            'terminal_no': parts[1],
            'time': parts[3]
        }
    elif data['type'] == 'network access point':
        data['data'] = {
            'terminal_no': parts[1],
            'name': parts[3],
            'user': parts[4],
            'pwd': parts[5]
        }
    elif data['type'] == 'answer mode':
        data['data'] = {
            'terminal_no': parts[1],
            'operation': parts[3]
        }
    elif data['type'] == 'IMEI setting':
        data['data'] = {
            'terminal_no': parts[1],
            'imei': parts[3],
            'time': parts[4]
        }
    elif data['type'] == 'language setting':
        data['data'] = {
            'terminal_no': parts[1],
            'language': parts[3],
            'time': parts[4]
        }
    elif data['type'] == 'audio monitor':
        data['data'] = {
            'terminal_no': parts[1],
            'time': parts[3]
        }
    elif data['type'] == 'power saving mode setting':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'query device information':
        data['data'] = {
            'terminal_no': parts[1]
        }
    else:
        data['data'] = {}

    # Convertir el diccionario a JSON
    json_data = json.dumps(data, indent=4)
    return json_data


def tcp_to_json(port, data):
    if port == 6001:
        print(f"{port}:{data}")
    elif port == 6013:
        data_json = parse_raw_data(data)
        print(f"{port}:{data_json}")
        # asyncio.run(broadcast(data_json["uniqueId"], type, data_json))


def handle_tcp_client(conn, addr):
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
