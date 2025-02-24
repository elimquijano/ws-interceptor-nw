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
    
    for i, j in enumerate(parts):
        print(f"Index: {i}, Value: {j}")

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
            'imei': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'data_valid_bit': parts[4],
            'latitude': float(parts[5][:2]) + float(parts[5][2:]) / 60,
            'longitude': float(parts[7][:3]) + float(parts[7][3:]) / 60,
            'speed': float(parts[9]),
            'course': float(parts[10]),
            'date': datetime.strptime(parts[11], '%d%m%y').strftime('%Y-%m-%d'),
            'vehicle_status': parts[12],
            'power_capacity': parts[13]
        }
    elif data['type'] == 'heartbeat packet':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'cut-off oil & engine/recovery oil & engine':
        data['data'] = {
            'imei': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S'),
            'ultimate_power_mode': parts[4],
            'cut_off_or_recovery': parts[5]
        }
    elif data['type'] == 'response to location request':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'fortification' or data['type'] == 'fortification version II':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'disarming' or data['type'] == 'disarming version II':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'main number bind':
        data['data'] = {
            'imei': parts[1],
            'num_list': parts[3]
        }
    elif data['type'] == 'server setting':
        data['data'] = {
            'imei': parts[1],
            'index': parts[3],
            'ip': parts[4],
            'port': parts[5],
            'domain': parts[6],
            'time': datetime.strptime(parts[7], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'terminal password setting':
        data['data'] = {
            'imei': parts[1],
            'old_password': parts[3],
            'new_password': parts[4]
        }
    elif data['type'] == 'interval setting':
        data['data'] = {
            'imei': parts[1],
            'interval': parts[3]
        }
    elif data['type'] == 'alarm setting':
        data['data'] = {
            'imei': parts[1],
            'key': parts[3],
            'type': parts[4]
        }
    elif data['type'] == 'device reboot':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'reset to defaults':
        data['data'] = {
            'imei': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'network access point':
        data['data'] = {
            'imei': parts[1],
            'name': parts[3],
            'user': parts[4],
            'pwd': parts[5]
        }
    elif data['type'] == 'answer mode':
        data['data'] = {
            'imei': parts[1],
            'operation': parts[3]
        }
    elif data['type'] == 'IMEI setting':
        data['data'] = {
            'imei': parts[1],
            'imei': parts[3],
            'time': datetime.strptime(parts[4], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'language setting':
        data['data'] = {
            'imei': parts[1],
            'language': parts[3],
            'time': datetime.strptime(parts[4], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'audio monitor':
        data['data'] = {
            'imei': parts[1],
            'time': datetime.strptime(parts[3], '%H%M%S').strftime('%H:%M:%S')
        }
    elif data['type'] == 'power saving mode setting':
        data['data'] = {
            'imei': parts[1]
        }
    elif data['type'] == 'query device information':
        data['data'] = {
            'imei': parts[1]
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
    if len(parts) > 0 and parts[0].startswith('imei:'):
        data['imei'] = parts[0].replace('imei:', '')
    else:
        data['imei'] = parts[0] if len(parts) > 0 else "unknown"
    
    # Determinar el tipo de evento (índice 1)
    if len(parts) > 1:
        command = parts[1]
        print(f"Command: {command}")  # Debug
        
        # Map command to event type exactamente como en los ejemplos
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
            print(f"Event type: {data['event_type']}")  # Debug
    else:
        data['event_type'] = 'unknown'
    
    # Parse datetime (índice 2 - format: DDMMYYHHMM o DDMMYYHHMM)
    if len(parts) > 2 and parts[2]:
        try:
            date_str = parts[2]
            print(f"Date string: {date_str}")  # Debug
            
            # Ensure we have at least 10 characters for DDMMYYHHMM
            if len(date_str) >= 10:
                # Parse DDMMYYHHMM format to datetime
                dt = datetime.strptime(date_str, '%d%m%y%H%M')
                # Format as YYYY-MM-DD HH:MM:SS
                data['datetime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                print(f"Parsed datetime: {data['datetime']}")  # Debug
            else:
                data['datetime'] = date_str  # Keep original if format doesn't match
        except ValueError as e:
            print(f"Error parsing datetime: {e}")  # Debug
            data['datetime'] = date_str  # Keep original if parsing fails
    
    # GPS validity is typically at index 5 ("A" means valid)
    if len(parts) > 5:
        for i in range(3, min(8, len(parts))):
            if parts[i] in ['A', 'V']:
                data['gps_valid'] = True if parts[i] == 'A' else False
                # If we found GPS validity, the next parts should be lat/long
                if i + 3 < len(parts):  # Need latitude, N/S, longitude, E/W
                    try:
                        # Get latitude
                        lat_str = parts[i+1]
                        lat_dir = parts[i+2]
                        
                        # Convert from DDMM.MMMM to decimal degrees
                        lat_deg = float(lat_str[:2])
                        lat_min = float(lat_str[2:])
                        lat_decimal = lat_deg + (lat_min / 60)
                        
                        # Apply direction
                        if lat_dir == 'S':
                            lat_decimal = -lat_decimal
                            
                        data['latitude'] = round(lat_decimal, 6)
                        
                        # Get longitude
                        lon_str = parts[i+3]
                        lon_dir = parts[i+4]
                        
                        # Convert from DDDMM.MMMM to decimal degrees
                        lon_deg = float(lon_str[:3])
                        lon_min = float(lon_str[3:])
                        lon_decimal = lon_deg + (lon_min / 60)
                        
                        # Apply direction
                        if lon_dir == 'W':
                            lon_decimal = -lon_decimal
                            
                        data['longitude'] = round(lon_decimal, 6)
                        
                        # Speed is typically after longitude direction
                        if i+5 < len(parts):
                            try:
                                data['speed'] = float(parts[i+5])
                            except ValueError:
                                pass
                    except Exception as e:
                        print(f"Error parsing coordinates: {e}")
                break
    
    # Looking specifically for the pattern from examples
    # Example: imei:353451044508750,help me,0809231929, ,F,055403.000,A,2233.1870,N,11354.3067,E,0.00,,;
    for i, part in enumerate(parts):
        if part == 'F' and i+2 < len(parts) and parts[i+1].endswith('.000') and parts[i+2] in ['A', 'V']:
            # We found the time field pattern
            if i+5 < len(parts):  # Need lat, N/S, lon, E/W
                try:
                    # GPS time
                    data['gps_time'] = parts[i+1]
                    
                    # GPS validity
                    data['gps_valid'] = True if parts[i+2] == 'A' else False
                    
                    # Get latitude
                    lat_str = parts[i+3]
                    lat_dir = parts[i+4]
                    
                    # Convert from DDMM.MMMM to decimal degrees
                    lat_deg = float(lat_str[:2])
                    lat_min = float(lat_str[2:])
                    lat_decimal = lat_deg + (lat_min / 60)
                    
                    # Apply direction
                    if lat_dir == 'S':
                        lat_decimal = -lat_decimal
                        
                    data['latitude'] = round(lat_decimal, 6)
                    
                    # Get longitude
                    lon_str = parts[i+5]
                    lon_dir = parts[i+6]
                    
                    # Convert from DDDMM.MMMM to decimal degrees
                    lon_deg = float(lon_str[:3])
                    lon_min = float(lon_str[3:])
                    lon_decimal = lon_deg + (lon_min / 60)
                    
                    # Apply direction
                    if lon_dir == 'W':
                        lon_decimal = -lon_decimal
                        
                    data['longitude'] = round(lon_decimal, 6)
                    
                    # Speed is typically after longitude direction
                    if i+7 < len(parts):
                        try:
                            data['speed'] = float(parts[i+7])
                        except ValueError:
                            pass
                except Exception as e:
                    print(f"Error parsing coordinates: {e}")
            break
    
    # Parse datetime in format DDMMYYHHMM to standard format
    if len(parts) > 2 and parts[2]:
        try:
            date_str = parts[2]
            if len(date_str) >= 10:
                # Add 20 to year for 21st century dates
                year = '20' + date_str[4:6]
                month = date_str[2:4]
                day = date_str[0:2]
                hour = date_str[6:8]
                minute = date_str[8:10]
                
                # Format as YYYY-MM-DD HH:MM:SS
                data['datetime'] = f"{year}-{month}-{day} {hour}:{minute}:00"
                print(f"Manually parsed datetime: {data['datetime']}")
        except Exception as e:
            print(f"Error manually parsing datetime: {e}")
    
    return data


def tcp_to_json(port, data):
    if port == 6001:
        pass
        #print(f"port: {port}, data: {data}")
        #data_json = parse_gps103_data(data)
        #print(data_json)
        # asyncio.run(broadcast(data_json["imei"], type, data_json))
    elif port == 6013:
        data_json = parse_h02_data(data)
        if data_json["type"] == "real-time location":
            type = "location"
        elif data_json["type"] == "device alarm":
            type = "event"
        else:
            type = None
        if type:
            asyncio.run(broadcast(data_json["data"]["imei"], type, data_json["data"]))

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
