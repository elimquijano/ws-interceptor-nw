import re
import json
import binascii
from datetime import datetime, timezone

class H02ProtocolDecoder:
    """
    Decodificador para el protocolo H02 usado en dispositivos de rastreo GPS
    Basado en el código del proyecto Traccar (https://github.com/traccar/traccar)
    """
    
    def __init__(self):
        # Patrones regex para diferentes formatos de mensajes
        self.PATTERN = re.compile(
            r'\*'
            r'..,'                                  # manufacturer
            r'(\d+)?,'                              # imei
            r'(?:V4,|V[^,]*,)'                      # version/response
            r'(?:(\d{2})(\d{2})(\d{2}))?,?'         # time (hhmmss)
            r'(?:([ABV])?|(\d+),)'                  # validity/coding scheme
            r'(?:-(d+)-(d+.\d+),([NS]),|'           # latitude format 1
            r'(\d+)(\d{2}\.\d+),([NS]),|'           # latitude format 2
            r'(\d+)(\d{2})(\d{4}),([NS]),)'         # latitude format 3
            r'(?:-(d+)-(d+.\d+),([EW]),|'           # longitude format 1
            r'(\d+)(\d{2}\.\d+),([EW]),|'           # longitude format 2
            r'(\d+)(\d{2})(\d{4}),([EW]),)'         # longitude format 3
            r' *(\d+\.?\d*),'                       # speed
            r'(\d+\.?\d*)?,'                        # course
            r'(?:\d+,)?'                            # battery
            r'(?:(\d{2})(\d{2})(\d{2}))?'           # date (ddmmyy)
            r'(?:,[^,]*,[^,]*,[^,]*)?'              # sim info (optional)
            r'(?:,(x{8})'                           # status
            r'(?:,(\d+),'                           # odometer
            r'(-?\d+),'                             # temperature
            r'(\d+\.\d+),'                          # fuel
            r'(-?\d+),'                             # altitude
            r'(x+),'                                # lac
            r'(x+)|'                                # cid
            r',(.*))?)?'                            # data
            r'#'
        )
        
        self.PATTERN_NBR = re.compile(
            r'\*'
            r'..,'                                  # manufacturer
            r'(\d+),'                               # imei
            r'NBR,'
            r'(\d{2})(\d{2})(\d{2}),'               # time (hhmmss)
            r'(\d+),'                               # mcc
            r'(\d+),'                               # mnc
            r'\d+,'                                 # gsm delay time
            r'\d+,'                                 # count
            r'((?:\d+,\d+,-?\d+,)+)'                # cells
            r'(\d{2})(\d{2})(\d{2}),'               # date (ddmmyy)
            r'([0-9a-fA-F]{8})'                     # status
        )
        
        self.PATTERN_LINK = re.compile(
            r'\*'
            r'..,'                                  # manufacturer
            r'(\d+),'                               # imei
            r'LINK,'
            r'(\d{2})(\d{2})(\d{2}),'               # time (hhmmss)
            r'(\d+),'                               # rssi
            r'(\d+),'                               # satellites
            r'(\d+),'                               # battery
            r'(\d+),'                               # steps
            r'(\d+),'                               # turnovers
            r'(\d{2})(\d{2})(\d{2}),'               # date (ddmmyy)
            r'([0-9a-fA-F]{8})'                     # status
        )
        
        self.PATTERN_V3 = re.compile(
            r'\*'
            r'..,'                                  # manufacturer
            r'(\d+),'                               # imei
            r'V3,'
            r'(\d{2})(\d{2})(\d{2}),'               # time (hhmmss)
            r'(\d{3})'                              # mcc
            r'(\d+),'                               # mnc
            r'(\d+),'                               # count
            r'(.*),'                                # cell info
            r'([0-9a-fA-F]{4}),'                    # battery
            r'\d+,'                                 # reboot info
            r'X,'
            r'(\d{2})(\d{2})(\d{2}),'               # date (ddmmyy)
            r'([0-9a-fA-F]{8})'                     # status
        )
        
        self.PATTERN_VP1 = re.compile(
            r'\*hq,'
            r'(\d{15}),'                            # imei
            r'VP1,'
            r'(?:V,'
            r'(\d+),'                               # mcc
            r'(\d+),'                               # mnc
            r'([^#]+)|'                             # cells
            r'[AB],'                                # validity
            r'(\d+)(\d{2}\.\d+),'                   # latitude
            r'([NS]),'
            r'(\d+)(\d{2}\.\d+),'                   # longitude
            r'([EW]),'
            r'(\d+\.\d+),'                          # speed
            r'(\d+\.\d+),'                          # course
            r'(\d{2})(\d{2})(\d{2}))'               # date (ddmmyy)
        )
        
        self.PATTERN_HTBT = re.compile(
            r'\*HQ,'
            r'(\d{15}),'                            # imei
            r'HTBT,'
            r'(\d+)'                                # battery
        )
    
    def process_status(self, status):
        """Procesa el campo de estado y devuelve un diccionario con las alarmas y estados"""
        result = {}
        alarms = []
        
        status_int = int(status, 16) if isinstance(status, str) else status
        
        if not (status_int & 0x1):
            alarms.append("vibration")
        elif not (status_int & 0x2) or not (status_int & 0x40000):
            alarms.append("sos")
        elif not (status_int & 0x4):
            alarms.append("overspeed")
        elif not (status_int & 0x80000):
            alarms.append("power_cut")
        
        if alarms:
            result["alarms"] = alarms
        
        result["ignition"] = bool(status_int & 0x400)
        result["status"] = status_int
        
        return result
    
    def decode_battery(self, value):
        """Decodifica el valor de la batería"""
        if value == 0:
            return None
        elif value <= 3:
            return (value - 1) * 10
        elif value <= 6:
            return (value - 1) * 20
        elif value <= 100:
            return value
        elif value >= 0xF1 and value <= 0xF6:
            return value - 0xF0
        else:
            return None
    
    def decode_text(self, message):
        """Decodifica mensajes en formato de texto"""
        match = self.PATTERN.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Intentar construir fecha y hora
        time_hour = groups[1]
        time_min = groups[2]
        time_sec = groups[3]
        date_day = groups[21]
        date_month = groups[22]
        date_year = groups[23]
        
        if time_hour and time_min and time_sec and date_day and date_month and date_year:
            timestamp = datetime(
                2000 + int(date_year), 
                int(date_month), 
                int(date_day),
                int(time_hour), 
                int(time_min), 
                int(time_sec), 
                tzinfo=timezone.utc
            )
            position["timestamp"] = timestamp.isoformat()
        else:
            position["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Validez de la posición
        if groups[4] == "A":
            position["valid"] = True
        elif groups[4] == "V":
            position["valid"] = False
        elif groups[5]:
            position["valid"] = True
        
        # Coordenadas
        lat_deg = None
        lat_min = None
        lat_dir = None
        lon_deg = None
        lon_min = None
        lon_dir = None
        
        # Intentar obtener la latitud y longitud de diferentes formatos posibles
        for i in range(6, 18):
            if groups[i]:
                if i >= 6 and i <= 9 and lat_deg is None:
                    lat_deg = groups[i]
                    lat_min = groups[i+1]
                    lat_dir = groups[i+2]
                elif i >= 12 and i <= 15 and lon_deg is None:
                    lon_deg = groups[i]
                    lon_min = groups[i+1]
                    lon_dir = groups[i+2]
        
        if lat_deg and lat_min and lat_dir and lon_deg and lon_min and lon_dir:
            lat = float(lat_deg) + float(lat_min) / 60
            if lat_dir == "S":
                lat = -lat
                
            lon = float(lon_deg) + float(lon_min) / 60
            if lon_dir == "W":
                lon = -lon
                
            position["latitude"] = lat
            position["longitude"] = lon
        
        # Velocidad y rumbo
        if groups[18]:
            position["speed"] = float(groups[18])
        if groups[19]:
            position["course"] = float(groups[19])
        
        # Estado y alarmas
        if groups[24]:
            status_data = self.process_status(groups[24])
            position.update(status_data)
        
        # Datos adicionales (odómetro, temperatura, combustible, etc.)
        if groups[25]:
            position["odometer"] = int(groups[25])
        if groups[26]:
            position["temperature"] = int(groups[26])
        if groups[27]:
            position["fuelLevel"] = float(groups[27])
        if groups[28]:
            position["altitude"] = int(groups[28])
        if groups[29] and groups[30]:
            position["network"] = {
                "cellTowers": [{
                    "lac": int(groups[29], 16),
                    "cid": int(groups[30], 16)
                }]
            }
        
        return position
    
    def decode_lbs(self, message):
        """Decodifica mensajes NBR (Location Based Service)"""
        match = self.PATTERN_NBR.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Construir fecha y hora
        time_hour = groups[1]
        time_min = groups[2]
        time_sec = groups[3]
        date_day = groups[7]
        date_month = groups[8]
        date_year = groups[9]
        
        timestamp = datetime(
            2000 + int(date_year), 
            int(date_month), 
            int(date_day),
            int(time_hour), 
            int(time_min), 
            int(time_sec), 
            tzinfo=timezone.utc
        )
        position["timestamp"] = timestamp.isoformat()
        
        # Datos de red celular
        mcc = int(groups[4])
        mnc = int(groups[5])
        cells_data = groups[6].split(',')
        
        cell_towers = []
        for i in range(0, len(cells_data) - 1, 3):
            if i + 2 < len(cells_data):
                cell_towers.append({
                    "mcc": mcc,
                    "mnc": mnc,
                    "lac": int(cells_data[i]),
                    "cid": int(cells_data[i + 1]),
                    "signalStrength": int(cells_data[i + 2])
                })
        
        position["network"] = {"cellTowers": cell_towers}
        
        # Estado y alarmas
        if groups[10]:
            status_data = self.process_status(groups[10])
            position.update(status_data)
        
        return position
    
    def decode_link(self, message):
        """Decodifica mensajes LINK"""
        match = self.PATTERN_LINK.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Construir fecha y hora
        time_hour = groups[1]
        time_min = groups[2]
        time_sec = groups[3]
        date_day = groups[10]
        date_month = groups[11]
        date_year = groups[12]
        
        timestamp = datetime(
            2000 + int(date_year), 
            int(date_month), 
            int(date_day),
            int(time_hour), 
            int(time_min), 
            int(time_sec), 
            tzinfo=timezone.utc
        )
        position["timestamp"] = timestamp.isoformat()
        
        # Datos adicionales
        position["rssi"] = int(groups[4])
        position["satellites"] = int(groups[5])
        position["batteryLevel"] = int(groups[6])
        position["steps"] = int(groups[7])
        position["turnovers"] = int(groups[8])
        
        # Estado y alarmas
        if groups[13]:
            status_data = self.process_status(groups[13])
            position.update(status_data)
        
        return position
    
    def decode_v3(self, message):
        """Decodifica mensajes V3"""
        match = self.PATTERN_V3.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Construir fecha y hora
        time_hour = groups[1]
        time_min = groups[2]
        time_sec = groups[3]
        date_day = groups[9]
        date_month = groups[10]
        date_year = groups[11]
        
        timestamp = datetime(
            2000 + int(date_year), 
            int(date_month), 
            int(date_day),
            int(time_hour), 
            int(time_min), 
            int(time_sec), 
            tzinfo=timezone.utc
        )
        position["timestamp"] = timestamp.isoformat()
        
        # Datos de red celular
        mcc = int(groups[4])
        mnc = int(groups[5])
        count = int(groups[6])
        cells_info = groups[7].split(',')
        
        cell_towers = []
        for i in range(count):
            if i * 4 + 1 < len(cells_info):
                cell_towers.append({
                    "mcc": mcc,
                    "mnc": mnc,
                    "lac": int(cells_info[i * 4]),
                    "cid": int(cells_info[i * 4 + 1])
                })
        
        position["network"] = {"cellTowers": cell_towers}
        position["battery"] = int(groups[8], 16)
        
        # Estado y alarmas
        if groups[12]:
            status_data = self.process_status(groups[12])
            position.update(status_data)
        
        return position
    
    def decode_vp1(self, message):
        """Decodifica mensajes VP1"""
        match = self.PATTERN_VP1.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Verificar si es un mensaje basado en celdas o en GPS
        if groups[1]:  # Cell-based
            # Datos de red celular
            mcc = int(groups[1])
            mnc = int(groups[2])
            cells = groups[3].split('Y')
            
            cell_towers = []
            for cell in cells:
                values = cell.split(',')
                if len(values) >= 3:
                    cell_towers.append({
                        "mcc": mcc,
                        "mnc": mnc,
                        "lac": int(values[0]),
                        "cid": int(values[1]),
                        "signalStrength": int(values[2])
                    })
            
            position["network"] = {"cellTowers": cell_towers}
            position["timestamp"] = datetime.now(timezone.utc).isoformat()
            
        else:  # GPS-based
            # Coordenadas
            lat_deg = int(groups[4])
            lat_min = float(groups[5])
            lat_dir = groups[6]
            lon_deg = int(groups[7])
            lon_min = float(groups[8])
            lon_dir = groups[9]
            
            lat = lat_deg + lat_min / 60
            if lat_dir == "S":
                lat = -lat
                
            lon = lon_deg + lon_min / 60
            if lon_dir == "W":
                lon = -lon
            
            position["latitude"] = lat
            position["longitude"] = lon
            position["valid"] = True
            position["speed"] = float(groups[10])
            position["course"] = float(groups[11])
            
            # Fecha y hora
            date_day = groups[12]
            date_month = groups[13]
            date_year = groups[14]
            
            timestamp = datetime(
                2000 + int(date_year), 
                int(date_month), 
                int(date_day),
                tzinfo=timezone.utc
            )
            position["timestamp"] = timestamp.isoformat()
        
        return position
    
    def decode_heartbeat(self, message):
        """Decodifica mensajes de heartbeat (latido)"""
        match = self.PATTERN_HTBT.match(message)
        if not match:
            return None
        
        groups = match.groups()
        device_id = groups[0]
        
        if not device_id:
            return None
        
        position = {
            "protocol": "h02", 
            "deviceId": device_id,
            "batteryLevel": int(groups[1]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return position
    
    def decode_binary(self, data):
        """Decodifica mensajes en formato binario (comenzando con $)"""
        if len(data) < 2:
            return None
            
        # Convertir bytes a hexadecimal
        hex_data = binascii.hexlify(data).decode('ascii')
        
        # Verificar si es un mensaje con ID largo o corto
        long_id = len(hex_data) == 84  # 42 bytes * 2
        
        if not (hex_data.startswith('24') or hex_data.startswith('$')):  # 24 es '$' en hex
            return None
        
        # Extraer el ID del dispositivo
        if long_id:
            device_id = hex_data[2:18]
            pos = 18
        else:
            device_id = hex_data[2:12]
            pos = 12
            
        position = {"protocol": "h02", "deviceId": device_id}
        
        # Decodificar fecha y hora
        hour = int(hex_data[pos:pos+2], 16)
        pos += 2
        minute = int(hex_data[pos:pos+2], 16)
        pos += 2
        second = int(hex_data[pos:pos+2], 16)
        pos += 2
        day = int(hex_data[pos:pos+2], 16)
        pos += 2
        month = int(hex_data[pos:pos+2], 16)
        pos += 2
        year = int(hex_data[pos:pos+2], 16) + 2000
        pos += 2
        
        timestamp = datetime(
            year, month, day, hour, minute, second, 
            tzinfo=timezone.utc
        )
        position["timestamp"] = timestamp.isoformat()
        
        # Decodificar latitud
        lat_deg = int(hex_data[pos:pos+2], 16) * 10
        pos += 2
        lat_deg += int(hex_data[pos:pos+2], 16)
        pos += 2
        
        # Nivel de batería
        battery_level = self.decode_battery(int(hex_data[pos:pos+2], 16))
        if battery_level is not None:
            position["batteryLevel"] = battery_level
        pos += 2
        
        # Decodificar longitud
        lon_deg = int(hex_data[pos:pos+2], 16) * 100
        pos += 2
        lon_deg += int(hex_data[pos:pos+2], 16) * 10
        pos += 2
        lon_deg += (int(hex_data[pos:pos+2], 16) & 0xF0) >> 4
        lon_min = (int(hex_data[pos:pos+2], 16) & 0x0F) * 10
        pos += 2
        
        # Leer bits de bandera para validez y dirección
        flags = int(hex_data[pos:pos+2], 16) & 0x0F
        pos += 2
        
        position["valid"] = (flags & 0x02) != 0
        
        # Calcular latitud y longitud finales
        lat_min = int(hex_data[pos:pos+10], 16) * 0.0001
        pos += 10
        lat = lat_deg + lat_min / 60
        if (flags & 0x04) == 0:
            lat = -lat
            
        lon_min += int(hex_data[pos:pos+8], 16) * 0.0001
        pos += 8
        lon = lon_deg + lon_min / 60
        if (flags & 0x08) == 0:
            lon = -lon
            
        position["latitude"] = lat
        position["longitude"] = lon
        
        # Velocidad
        speed = int(hex_data[pos:pos+6], 16)
        pos += 6
        position["speed"] = speed
        
        # Curso
        course_high = int(hex_data[pos:pos+2], 16) & 0x0F
        pos += 2
        course_low = int(hex_data[pos:pos+2], 16)
        pos += 2
        position["course"] = course_high * 100.0 + course_low
        
        # Estado
        status = int(hex_data[pos:pos+8], 16)
        pos += 8
        status_data = self.process_status(status)
        position.update(status_data)
        
        return position
    
    def decode(self, message):
        """
        Decodifica un mensaje del protocolo H02 y devuelve un objeto JSON
        
        Args:
            message: Mensaje en formato string o bytes
            
        Returns:
            Diccionario con los datos decodificados o None si no se pudo decodificar
        """
        if isinstance(message, bytes):
            # Si el mensaje comienza con $, es binario
            if message.startswith(b'$'):
                result = self.decode_binary(message)
            else:
                # Intentar convertir a texto
                try:
                    message_str = message.decode('ascii', 'ignore').strip()
                    result = self.decode(message_str)
                except:
                    return None
        elif isinstance(message, str):
            message = message.strip()
            # Determinar tipo de mensaje basado en prefijo/formato
            if message.startswith('*'):
                if ',NBR,' in message:
                    result = self.decode_lbs(message)
                elif ',LINK,' in message:
                    result = self.decode_link(message)
                elif ',V3,' in message:
                    result = self.decode_v3(message)
                elif ',VP1,' in message:
                    result = self.decode_vp1(message)
                elif ',HTBT,' in message or ',V0,' in message:
                    result = self.decode_heartbeat(message)
                else:
                    result = self.decode_text(message)
            else:
                return None
        else:
            return None
            
        return result
    
    def to_json(self, message):
        """
        Decodifica un mensaje y lo devuelve como JSON formateado
        
        Args:
            message: Mensaje en formato string o bytes
            
        Returns:
            String con el JSON formateado o None si no se pudo decodificar
        """
        result = self.decode(message)
        if result:
            return json.dumps(result, indent=2)
        return None

def decode_h02(message):
    decoder = H02ProtocolDecoder()
    return decoder.to_json(message)