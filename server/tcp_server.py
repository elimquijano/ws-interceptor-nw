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

    # Check if this is the new format (starts with "imei:")
    if parts[0].startswith('imei:'):
        # Extract the IMEI from the first part
        imei = parts[0].replace('imei:', '')
        # Adjust parts list to match the expected format
        adjusted_parts = [imei] + parts[1:]
        parts = adjusted_parts

    # Determinar el tipo de evento
    command = parts[1] if len(parts) > 1 else "unknown"
    print(f"command: {command}")
    
    # Determine event type (this part remains the same)
    if command == 'A':
        data['type'] = 'Log on request'
    elif command == 'help me':
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
    # ... remaining command type checks remain the same ...
    else:
        data['type'] = 'unknown'

    # Try to extract data based on the format provided in your example
    try:
        # Format appears to be: imei:NUMBER,COMMAND,DATE,BATTERY%,F,TIME,GPS_VALID,LAT,LAT_DIR,LON,LON_DIR,...
        if data['type'] == 'ACC alarm' and len(parts) >= 12:
            data['data'] = {
                'imei': parts[0],
                'time': parts[2],  # Original timestamp format
                'battery_percentage': parts[3],
                'flag': parts[4],  # 'F' value that caused the error
                'time_gps': parts[5],
                'gps_valid': parts[6],
                'latitude': parts[7],  # Keep as string to avoid parsing errors
                'latitude_direction': parts[8],
                'longitude': parts[9],  # Keep as string to avoid parsing errors
                'longitude_direction': parts[10],
            }
            
            # Try to parse latitude and longitude if possible
            try:
                if parts[7] and parts[7] != "":
                    data['data']['latitude_decimal'] = float(parts[7][:2]) + float(parts[7][2:]) / 60
                if parts[9] and parts[9] != "":
                    data['data']['longitude_decimal'] = float(parts[9][:3]) + float(parts[9][3:]) / 60
            except (ValueError, IndexError):
                # If conversion fails, keep the original string values only
                pass
                
        # If the format doesn't match any known pattern, store all parts as raw data
        else:
            data['data'] = {'raw_parts': parts}
            
    except Exception as e:
        # If there's any error in parsing, store raw data and the error
        data['error'] = str(e)
        data['raw_data'] = raw_data
        data['parts'] = parts

    # Convertir el diccionario a JSON
    json_data = json.dumps(data, indent=4)
    return json_data


def tcp_to_json(port, data):
    if port == 6001:
        #pass
        print(f"port: {port}, data: {data}")
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
