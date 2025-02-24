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
    
    # Extract IMEI from the first part (handling the "imei:" prefix)
    if parts[0].startswith('imei:'):
        data['imei'] = parts[0].replace('imei:', '')
    else:
        data['imei'] = parts[0]
    
    # Determinar el tipo de evento
    if len(parts) > 1:
        command = parts[1]
        
        # Map command to event type
        event_types = {
            'help me': 'SOS alarm',
            'low battery': 'low battery alarm',
            'move': 'movement alarm',
            'speed': 'over speed alarm',
            'stockade': 'geo-fence alarm',
            'ac alarm': 'power off alarm',
            'door alarm': 'door alarm',
            'sensor alarm': 'shock sensor alarm',
            'acc alarm': 'ACC alarm',
            'accident alarm': 'accident alarm',
            'bonnet alarm': 'bonnet alarm',
            'footbrake alarm': 'footbrake alarm',
            'oil': 'oil leak/oil theft alarm',
            'oil1': 'oil 1 alarm',
            'oil2': 'oil 2 alarm',
            '001': 'location information',
            '101': 'track upon time interval',
            '103': 'track upon distance interval'
        }
        
        # Special case for temperature alarm
        if command.startswith('T:'):
            data['event_type'] = 'temperature alarm'
            data['temperature'] = command.replace('T:', '')
        else:
            data['event_type'] = event_types.get(command, 'unknown')
            
            # Extract oil percentage for oil alarm
            if command == 'oil' and len(parts) > 2 and parts[2]:
                try:
                    data['oil_percentage'] = float(parts[2])
                except ValueError:
                    pass
    else:
        data['event_type'] = 'unknown'
    
    # Parse datetime (format: DDMMYYHHMM)
    if len(parts) > 2 and parts[2] and len(parts[2]) >= 10:
        try:
            date_str = parts[2]
            # Parse DDMMYYHHMM format to datetime
            dt = datetime.strptime(date_str, '%d%m%y%H%M')
            # Format as YYYY-MM-DD HH:MM:SS
            data['datetime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            data['datetime'] = parts[2]  # Keep original if parsing fails
    
    # Parse coordinates
    # Format: DDDMM.MMMM,N/S for latitude and DDDMM.MMMM,E/W for longitude
    lat_index = None
    lon_index = None
    
    # Find indexes for latitude and longitude based on common patterns
    for i in range(len(parts)):
        if i + 1 < len(parts) and parts[i+1] in ['N', 'S']:
            lat_index = i
        if i + 1 < len(parts) and parts[i+1] in ['E', 'W']:
            lon_index = i
    
    # Parse latitude if found
    if lat_index is not None and lat_index + 1 < len(parts):
        try:
            lat_str = parts[lat_index]
            lat_dir = parts[lat_index + 1]
            
            # Convert from DDMM.MMMM to decimal degrees
            lat_deg = float(lat_str[:2])
            lat_min = float(lat_str[2:])
            lat_decimal = lat_deg + (lat_min / 60)
            
            # Apply direction
            if lat_dir == 'S':
                lat_decimal = -lat_decimal
                
            data['latitude'] = round(lat_decimal, 6)
        except (ValueError, IndexError):
            pass
    
    # Parse longitude if found
    if lon_index is not None and lon_index + 1 < len(parts):
        try:
            lon_str = parts[lon_index]
            lon_dir = parts[lon_index + 1]
            
            # Convert from DDDMM.MMMM to decimal degrees
            lon_deg = float(lon_str[:3])
            lon_min = float(lon_str[3:])
            lon_decimal = lon_deg + (lon_min / 60)
            
            # Apply direction
            if lon_dir == 'W':
                lon_decimal = -lon_decimal
                
            data['longitude'] = round(lon_decimal, 6)
        except (ValueError, IndexError):
            pass
    
    # Parse speed if available (typically after longitude direction)
    if lon_index is not None and lon_index + 2 < len(parts):
        try:
            data['speed'] = float(parts[lon_index + 2])
        except (ValueError, IndexError):
            pass
    
    # Parse ACC state (common in location messages)
    for i in range(len(parts)):
        if i+3 < len(parts) and parts[i].endswith('%') and parts[i+1].endswith('%'):
            try:
                # ACC state is typically after oil percentages
                acc_state = int(parts[i+2])
                data['acc_state'] = 'ON' if acc_state == 1 else 'OFF'
            except (ValueError, IndexError):
                pass
    
    # Parse additional information based on event type
    if data['event_type'] == 'oil leak/oil theft alarm' and 'oil_percentage' not in data:
        # Try to find oil percentage in other positions
        for part in parts:
            if part.endswith('%'):
                try:
                    data['oil_percentage'] = float(part.replace('%', ''))
                    break
                except ValueError:
                    pass
    
    # For dual fuel sensor alarms
    if data['event_type'] in ['oil 1 alarm', 'oil 2 alarm']:
        # Try to find both oil percentages
        for i in range(len(parts)):
            if parts[i].endswith('%') and i+1 < len(parts) and parts[i+1].endswith('%'):
                try:
                    data['oil1_percentage'] = float(parts[i].replace('%', ''))
                    data['oil2_percentage'] = float(parts[i+1].replace('%', ''))
                    break
                except ValueError:
                    pass
    
    return data


def tcp_to_json(port, data):
    if port == 6001:
        #pass
        print(f"port: {port}, data: {data}")
        data_json = parse_gps103_data(data)
        print(data_json)
        # asyncio.run(broadcast(data_json["imei"], type, data_json))
    elif port == 6013:
        #print(f"port: {port}, data: {data}")
        data_json = parse_h02_data(data)
        print(data_json)
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
