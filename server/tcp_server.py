import socket
import json
import threading
import asyncio
from datetime import datetime, timedelta
from .utils import broadcast

def parse_h02_data(raw_data):
    # Dividir el string en partes
    parts = raw_data.strip().split(',')

    # Inicializar un diccionario para almacenar la información
    data = {}

    # Determinar el tipo de evento
    command = parts[2]
    if command == 'V1':
        data['type'] = 'real-time location'
    elif command == 'XT':
        data['type'] = 'heartbeat packet'
    elif command == 'VI1':
        data['type'] = 'location request'
    elif command == 'BC':
        data['type'] = 'blind spots uploading'
    elif command == 'ALRM':
        data['type'] = 'device alarm'
    elif command == 'S20':
        data['type'] = 'cut-off oil & engine/recovery oil & engine'
    elif command == 'CR':
        data['type'] = 'response to location request'
    elif command == 'SF':
        data['type'] = 'fortification'
    elif command == 'SF2':
        data['type'] = 'fortification version II'
    elif command == 'CF':
        data['type'] = 'disarming'
    elif command == 'CF2':
        data['type'] = 'disarming version II'
    elif command == 'UR':
        data['type'] = 'main number bind'
    elif command == 'IP':
        data['type'] = 'server setting'
    elif command == 'MP':
        data['type'] = 'terminal password setting'
    elif command == 'XT/NXT':
        data['type'] = 'interval setting'
    elif command == 'KC':
        data['type'] = 'alarm setting'
    elif command == 'CQ':
        data['type'] = 'device reboot'
    elif command == 'RESET':
        data['type'] = 'reset to defaults'
    elif command == 'APN':
        data['type'] = 'network access point'
    elif command == 'ACPC':
        data['type'] = 'answer mode'
    elif command == 'SIMEI':
        data['type'] = 'IMEI setting'
    elif command == 'SLAN':
        data['type'] = 'language setting'
    elif command == 'CALB':
        data['type'] = 'audio monitor'
    elif command == 'PWM':
        data['type'] = 'power saving mode setting'
    elif command == 'INFO':
        data['type'] = 'query device information'
    else:
        data['type'] = 'unknown'

    # Extraer los datos según el tipo de evento
    if data['type'] in ['real-time location', 'location request', 'blind spots uploading', 'device alarm']:
        data['data'] = {
            'terminal_no': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'data_valid_bit': parts[4],
            'latitude': float(parts[5][:2]) + float(parts[5][2:]) / 60,
            'latitude_direction': parts[6],
            'longitude': float(parts[7][:3]) + float(parts[7][3:]) / 60,
            'longitude_direction': parts[8],
            'speed': float(parts[9]),
            'direction': float(parts[10]),
            'date': datetime.strptime(parts[11], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[12],
            'power_capacity': parts[13]
        }
    elif data['type'] == 'heartbeat packet':
        data['data'] = {
            'terminal_no': parts[1]
        }
    elif data['type'] == 'cut-off oil & engine/recovery oil & engine':
        data['data'] = {
            'terminal_no': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
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
            'time': datetime.strptime(parts[7], '%H%M%S').strftime('%H:%M:%S')
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
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S')
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
            'time': datetime.strptime(parts[4], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'language setting':
        data['data'] = {
            'terminal_no': parts[1],
            'language': parts[3],
            'time': datetime.strptime(parts[4], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'audio monitor':
        data['data'] = {
            'terminal_no': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S')
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

def parse_gps103_data(raw_data):
    # Dividir el string en partes
    parts = raw_data.strip().split(',')

    # Inicializar un diccionario para almacenar la información
    data = {}

    # Determinar el tipo de evento
    command = parts[1]
    print(f"command: {command}")
    if command == 'help me':
        data['type'] = 'SOS alarm'
    elif command == 'low battery':
        data['type'] = 'low battery alarm'
    elif command == 'move':
        data['type'] = 'movement alarm'
    elif command == 'speed':
        data['type'] = 'over speed alarm'
    elif command == 'stockade':
        data['type'] = 'geo-fence alarm'
    elif command == 'ac alarm':
        data['type'] = 'ACC alarm'
    elif command == 'accident alarm':
        data['type'] = 'accident alarm'
    elif command == 'sensor alarm':
        data['type'] = 'shock sensor alarm'
    elif command == 'door alarm':
        data['type'] = 'door alarm'
    elif command == 'oil':
        data['type'] = 'oil leak/oil theft alarm'
    elif command == 'DTC':
        data['type'] = 'vehicle fault notification'
    elif command == 'service':
        data['type'] = 'vehicle maintenance notification'
    elif command == '001':
        data['type'] = 'location information'
    elif command == '101':
        data['type'] = 'track upon time interval'
    elif command == '103':
        data['type'] = 'track upon distance interval'
    elif command == '102':
        data['type'] = 'cancel auto track continuously'
    elif command == '104':
        data['type'] = 'cancel alarm'
    elif command == '105':
        data['type'] = 'set movement alarm'
    elif command == '106':
        data['type'] = 'cancel movement alarm'
    elif command == '107':
        data['type'] = 'set overspeed alarm'
    elif command == '108':
        data['type'] = 'set time zone'
    elif command == '109':
        data['type'] = 'cut off oil and power'
    elif command == '110':
        data['type'] = 'resume oil and power'
    elif command == '111':
        data['type'] = 'arm'
    elif command == '112':
        data['type'] = 'disarm'
    elif command == '113':
        data['type'] = 'switch to SMS mode'
    elif command == '114':
        data['type'] = 'set geo-fence'
    elif command == '115':
        data['type'] = 'cancel geo-fence'
    elif command == '116':
        data['type'] = 'data load'
    elif command == '117':
        data['type'] = 'cancel upload'
    elif command == '118':
        data['type'] = 'activate less GPRS mode'
    elif command == '119':
        data['type'] = 'deactivate less GPRS mode'
    elif command == '120':
        data['type'] = 'automatic update positions of vehicle turns'
    elif command == '121':
        data['type'] = 'set multi-area management'
    elif command == '122':
        data['type'] = 'set IP, port for address function'
    elif command == '150':
        data['type'] = 'activate speed limit mode'
    elif command == '151':
        data['type'] = 'deactivate speed limit mode'
    elif command == '152':
        data['type'] = 'activate speed limit'
    elif command == '125':
        data['type'] = 'remote start'
    elif command == '525':
        data['type'] = 'turn off the engine'
    elif command == '526':
        data['type'] = 'appointment'
    elif command == '160':
        data['type'] = 'server request photo'
    elif command == '161':
        data['type'] = 'server request photo retransmission'
    elif command == '170':
        data['type'] = 'send LCD/Handset, dispatch screen (notice)'
    elif command == '171':
        data['type'] = 'phone call dispatch: center sends answer race request'
    elif command == '172':
        data['type'] = 'phone call dispatch: center sends answer successfully'
    elif command == '173':
        data['type'] = 'phone call dispatch: center sends answer failed'
    elif command == '174':
        data['type'] = 'phone call dispatch: center cancels order'
    elif command == '175':
        data['type'] = 'driver hands in answer order'
    elif command == '176':
        data['type'] = 'driver cancels order'
    elif command == '177':
        data['type'] = 'driver finishes task'
    elif command == '180':
        data['type'] = 'add ads'
    elif command == '181':
        data['type'] = 'delete ads'
    elif command == 'rfid':
        data['type'] = 'RFID'
    elif command == 'TPMS':
        data['type'] = 'tyre pressure monitoring'
    else:
        data['type'] = 'unknown'

    # Extraer los datos según el tipo de evento
    if data['type'] in ['location information', 'SOS alarm', 'low battery alarm', 'movement alarm', 'over speed alarm', 'geo-fence alarm', 'ACC alarm', 'accident alarm', 'shock sensor alarm', 'door alarm', 'oil leak/oil theft alarm', 'vehicle fault notification', 'vehicle maintenance notification']:
        data['data'] = {
            'imei': parts[0],
            'time': datetime.strptime(parts[2], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[3],
            'latitude': float(parts[4][:2]) + float(parts[4][2:]) / 60,
            'latitude_direction': parts[5],
            'longitude': float(parts[6][:3]) + float(parts[6][3:]) / 60,
            'longitude_direction': parts[7],
            'speed': float(parts[8]),
            'direction': float(parts[9]),
            'date': datetime.strptime(parts[10], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[11],
            'oil_percentage_1': parts[12],
            'oil_percentage_2': parts[13],
            'temperature': parts[14]
        }
    elif data['type'] in ['track upon time interval', 'track upon distance interval', 'cancel auto track continuously', 'cancel alarm', 'set movement alarm', 'cancel movement alarm', 'set overspeed alarm', 'set time zone', 'cut off oil and power', 'resume oil and power', 'arm', 'disarm', 'switch to SMS mode', 'set geo-fence', 'cancel geo-fence', 'data load', 'cancel upload', 'activate less GPRS mode', 'deactivate less GPRS mode', 'automatic update positions of vehicle turns', 'set multi-area management', 'set IP, port for address function', 'activate speed limit mode', 'deactivate speed limit mode', 'activate speed limit']:
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'time': datetime.strptime(parts[2], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[3],
            'latitude': float(parts[4][:2]) + float(parts[4][2:]) / 60,
            'latitude_direction': parts[5],
            'longitude': float(parts[6][:3]) + float(parts[6][3:]) / 60,
            'longitude_direction': parts[7],
            'speed': float(parts[8]),
            'direction': float(parts[9]),
            'date': datetime.strptime(parts[10], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[11],
            'oil_percentage_1': parts[12],
            'oil_percentage_2': parts[13],
            'temperature': parts[14]
        }
    elif data['type'] in ['remote start', 'turn off the engine', 'appointment']:
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'time': datetime.strptime(parts[2], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[3],
            'latitude': float(parts[4][:2]) + float(parts[4][2:]) / 60,
            'latitude_direction': parts[5],
            'longitude': float(parts[6][:3]) + float(parts[6][3:]) / 60,
            'longitude_direction': parts[7],
            'speed': float(parts[8]),
            'direction': float(parts[9]),
            'date': datetime.strptime(parts[10], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[11],
            'oil_percentage_1': parts[12],
            'oil_percentage_2': parts[13],
            'temperature': parts[14]
        }
    elif data['type'] in ['server request photo', 'server request photo retransmission']:
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'photo_data_amount': parts[2],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'phone_number': parts[4],
            'gps_valid': parts[5],
            'latitude': float(parts[6][:2]) + float(parts[6][2:]) / 60,
            'latitude_direction': parts[7],
            'longitude': float(parts[8][:3]) + float(parts[8][3:]) / 60,
            'longitude_direction': parts[9],
            'speed': float(parts[10]),
            'direction': float(parts[11]),
            'date': datetime.strptime(parts[12], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[13],
            'oil_percentage_1': parts[14],
            'oil_percentage_2': parts[15],
            'temperature': parts[16]
        }
    elif data['type'] in ['send LCD/Handset, dispatch screen (notice)', 'phone call dispatch: center sends answer race request', 'phone call dispatch: center sends answer successfully', 'phone call dispatch: center sends answer failed', 'phone call dispatch: center cancels order', 'driver hands in answer order', 'driver cancels order', 'driver finishes task']:
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'order_no': parts[2],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[4],
            'latitude': float(parts[5][:2]) + float(parts[5][2:]) / 60,
            'latitude_direction': parts[6],
            'longitude': float(parts[7][:3]) + float(parts[7][3:]) / 60,
            'longitude_direction': parts[8],
            'speed': float(parts[9]),
            'direction': float(parts[10]),
            'date': datetime.strptime(parts[11], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[12],
            'oil_percentage_1': parts[13],
            'oil_percentage_2': parts[14],
            'temperature': parts[15]
        }
    elif data['type'] in ['add ads', 'delete ads']:
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'ad_code': parts[2],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[4],
            'latitude': float(parts[5][:2]) + float(parts[5][2:]) / 60,
            'latitude_direction': parts[6],
            'longitude': float(parts[7][:3]) + float(parts[7][3:]) / 60,
            'longitude_direction': parts[8],
            'speed': float(parts[9]),
            'direction': float(parts[10]),
            'date': datetime.strptime(parts[11], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[12],
            'oil_percentage_1': parts[13],
            'oil_percentage_2': parts[14],
            'temperature': parts[15]
        }
    elif data['type'] == 'RFID':
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'rfid_tag': parts[2],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'gps_valid': parts[4],
            'latitude': float(parts[5][:2]) + float(parts[5][2:]) / 60,
            'latitude_direction': parts[6],
            'longitude': float(parts[7][:3]) + float(parts[7][3:]) / 60,
            'longitude_direction': parts[8],
            'speed': float(parts[9]),
            'direction': float(parts[10]),
            'date': datetime.strptime(parts[11], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[12],
            'oil_percentage_1': parts[13],
            'oil_percentage_2': parts[14],
            'temperature': parts[15]
        }
    elif data['type'] == 'tyre pressure monitoring':
        data['data'] = {
            'imei': parts[0],
            'command': parts[1],
            'time': datetime.strptime(parts[2], '%H%M%S').strftime('%H:%M:%S'),
            'tyre_status': parts[3],
            'left_front_tyre_pressure': parts[4],
            'left_front_tyre_temperature': parts[5],
            'left_front_tyre_status': parts[6],
            'right_front_tyre_pressure': parts[7],
            'right_front_tyre_temperature': parts[8],
            'right_front_tyre_status': parts[9],
            'left_rear_tyre_pressure': parts[10],
            'left_rear_tyre_temperature': parts[11],
            'left_rear_tyre_status': parts[12],
            'right_rear_tyre_pressure': parts[13],
            'right_rear_tyre_temperature': parts[14],
            'right_rear_tyre_status': parts[15]
        }
    else:
        data['data'] = {}

    # Convertir el diccionario a JSON
    json_data = json.dumps(data, indent=4)
    return json_data

def tcp_to_json(port, data):
    if port == 6001:
        #pass
        #print(f"port: {port}, data: {data}")
        data_json = parse_gps103_data(data)
        print(data_json)
        # asyncio.run(broadcast(data_json["imei"], type, data_json))
    elif port == 6013:
        pass
        #print(f"port: {port}, data: {data}")
        #data_json = parse_h02_data(data)
        #print(data_json)
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
