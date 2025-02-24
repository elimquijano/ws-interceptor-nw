import re
import json
import datetime
import binascii
from typing import Dict, Optional, Tuple, List, Any, Union

class Gps103Decoder:
    """
    Decodificador para el protocolo GPS103, basado en la implementación de Traccar.
    Convierte mensajes del protocolo a formato JSON.
    """
    
    def __init__(self):
        # Patrones de expresiones regulares similares a los del código Java
        self.PATTERN = re.compile(
            r"imei:(\d+),"                      # imei
            r"([^,]*),"                         # alarma
            r"(?:(\d{2})/?(\d{2})/?(\d{2}) ?"   # fecha local (yymmdd)
            r"(\d{2}):?(\d{2})(?:\d{2})?,|(?:\d*),)"  # hora local (hhmmss)
            r"([^,]+)?,"                        # rfid
            r"(?:L,(?:,,([x\d]+),,([x\d]+),,,)?|"  # lac, cid
            r"F,(?:(\d{2})(\d{2})(\d{2})(?:.\d+)?|(?:\d{1,5}.\d+)?),([AV])," # hora utc, validez
            r"(?:([NS]),)?(\d+)(\d{2}.\d+),(?:([NS]),)?(?:([EW]),)?(\d+)(\d{2}.\d+),(?:([EW])?,)?" # lat, lon
            r"(\d+.?\d*)?(?:,(\d+.?\d*))?(?:,(-?\d+.?\d*))?"  # velocidad, curso, altitud
            r"(?:,([01]))?(?:,([01]))?"  # ignición, puerta
            r"(?:,(?:(\d+.\d+)%)?(?:,(?:(\d+.\d+)%|\d+)?))?"  # combustible 1, combustible 2
            r"(?:,([-+]?\d+))?)"  # temperatura
            r".*"
        )
        
        self.PATTERN_OBD = re.compile(
            r"imei:(\d+),"                      # imei
            r"OBD,"                             # tipo
            r"(\d{2})(\d{2})(\d{2})"            # fecha (yymmdd)
            r"(\d{2})(\d{2})(\d{2}),"           # hora (hhmmss)
            r"(\d+)?,"                          # odómetro
            r"(\d+.\d+)?,"                      # combustible instantáneo
            r"(\d+.\d+)?,"                      # combustible promedio
            r"(\d+)?,"                          # horas
            r"(\d+),"                           # velocidad
            r"(\d+.?\d*%),"                     # carga de potencia
            r"(?:([-+]?\d+)|[-+]?),"            # temperatura
            r"(\d+.?\d*%),"                     # acelerador
            r"(\d+),"                           # rpm
            r"(\d+.\d+),"                       # batería
            r"([^;]*)"                          # dtcs
            r".*"
        )
        
        self.PATTERN_ALT = re.compile(
            r"imei:(\d+),"                      # imei
            r"[^,]+,"
            r"(?:-+|(.+)),"                     # evento
            r"(?:-+|(.+)),"                     # id del sensor
            r"(?:-+|(.+)),"                     # voltaje del sensor
            r"(\d{2})(\d{2})(\d{2}),"           # hora (hhmmss)
            r"(\d{2})(\d{2})(\d{2}),"           # fecha (ddmmyy)
            r"(\d+),"                           # rssi
            r"(\d),"                            # estado gps
            r"(-?\d+.\d+),"                     # latitud
            r"(-?\d+.\d+),"                     # longitud
            r"(\d+),"                           # velocidad
            r"(\d+),"                           # curso
            r"(-?\d+),"                         # altitud
            r"(\d+.\d+),"                       # hdop
            r"(\d+),"                           # satélites
            r"([01]),"                          # ignición
            r"([01]),"                          # carga
            r"(?:-+|(.+))"                      # error
            r".*"
        )
        
        self.photo_packets = 0
        self.photo_data = bytearray()
        
        # Constantes de alarma (similares a las del código de Traccar)
        self.ALARM_TYPES = {
            "help me": "sos",
            "low battery": "lowBattery",
            "stockade": "geofence",
            "move": "movement",
            "speed": "overspeed",
            "door alarm": "door",
            "ac alarm": "powerCut",
            "accident alarm": "accident",
            "sensor alarm": "vibration",
            "bonnet alarm": "bonnet",
            "footbrake alarm": "footBrake",
            "DTC": "fault"
        }
    
    def decode_alarm(self, value: str) -> Optional[str]:
        """Decodifica el tipo de alarma"""
        if value.startswith("T:"):
            return "temperature"
        elif value.startswith("oil"):
            return "fuelLeak"
        return self.ALARM_TYPES.get(value)
    
    def decode_regular(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Decodifica mensajes regulares del protocolo GPS103"""
        match = self.PATTERN.match(sentence)
        if not match:
            return None
        
        groups = match.groups()
        imei = groups[0]
        
        position = {
            "protocol": "gps103",
            "deviceId": imei,
            "attributes": {}
        }
        
        # Alarma
        alarm = groups[1]
        alarm_type = self.decode_alarm(alarm)
        if alarm_type:
            position["alarm"] = alarm_type
            
        if alarm == "help me":
            # En el código Java, envía una respuesta "**,imei:{imei},E;"
            pass
        elif alarm.startswith("vt"):
            self.photo_packets = int(alarm[2:])
            self.photo_data = bytearray()
        elif alarm == "acc on":
            position["attributes"]["ignition"] = True
        elif alarm == "acc off":
            position["attributes"]["ignition"] = False
        elif alarm.startswith("T:"):
            position["attributes"]["temp1"] = float(alarm[2:])
        elif alarm.startswith("oil "):
            position["attributes"]["fuelLevel"] = float(alarm[4:])
        elif "alarm" not in position and alarm != "tracker":
            position["attributes"]["event"] = alarm
            
        # Fecha y hora
        try:
            year = int(groups[2] or 0)
            month = int(groups[3] or 0)
            day = int(groups[4] or 0)
            hour = int(groups[5] or 0)
            minute = int(groups[6] or 0)
            
            rfid = groups[7]
            if alarm == "rfid":
                position["attributes"]["driverUniqueId"] = rfid
                
            # Celdas
            if groups[8] and groups[9]:
                position["attributes"]["network"] = {
                    "cellTowers": [{
                        "lac": int(groups[8], 16),
                        "cid": int(groups[9], 16)
                    }]
                }
                
            # Procesamos el resto de la información
            if groups[10]:  # Si hay información UTC
                utc_hour = int(groups[10])
                utc_minute = int(groups[11])
                utc_second = int(groups[12] or 0)
                
                # Ajuste de zona horaria similar al código Java
                # Aquí simplificamos un poco
                dt = datetime.datetime(2000 + year if year < 100 else year, 
                                      month or 1, day or 1, hour or 0, minute or 0, 0)
                
                position["deviceTime"] = dt.isoformat() + "Z"
                
                # Validez
                validity = groups[13] == "A"
                position["valid"] = validity
                
                # Coordenadas
                lat_hem = groups[14] or groups[16] or "N"
                lat_deg = float(groups[15])
                lat_min = float(groups[16] or 0)
                lat = lat_deg + lat_min / 60
                if lat_hem == "S":
                    lat = -lat
                    
                lon_hem = groups[17] or groups[20] or "E"
                lon_deg = float(groups[18])
                lon_min = float(groups[19] or 0)
                lon = lon_deg + lon_min / 60
                if lon_hem == "W":
                    lon = -lon
                    
                position["latitude"] = lat
                position["longitude"] = lon
                
                # Velocidad, curso, altitud
                if groups[21]:
                    position["speed"] = float(groups[21])
                if groups[22]:
                    position["course"] = float(groups[22])
                if groups[23]:
                    position["altitude"] = float(groups[23])
                    
                # Ignición y puerta
                if groups[24]:
                    position["attributes"]["ignition"] = groups[24] == "1"
                if groups[25]:
                    position["attributes"]["door"] = groups[25] == "1"
                    
                # Combustible
                if groups[26]:
                    position["attributes"]["fuel1"] = float(groups[26])
                if groups[27]:
                    position["attributes"]["fuel2"] = float(groups[27])
                    
                # Temperatura
                if groups[28]:
                    position["attributes"]["temp1"] = int(groups[28])
                    
        except (ValueError, IndexError) as e:
            print(f"Error al decodificar mensaje: {e}")
            return None
            
        return position
    
    def decode_obd(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Decodifica mensajes OBD del protocolo GPS103"""
        match = self.PATTERN_OBD.match(sentence)
        if not match:
            return None
        
        groups = match.groups()
        imei = groups[0]
        
        position = {
            "protocol": "gps103",
            "deviceId": imei,
            "attributes": {}
        }
        
        try:
            # Fecha y hora
            year = int(groups[1])
            month = int(groups[2])
            day = int(groups[3])
            hour = int(groups[4])
            minute = int(groups[5])
            second = int(groups[6])
            
            dt = datetime.datetime(2000 + year if year < 100 else year, 
                                  month, day, hour, minute, second)
            position["deviceTime"] = dt.isoformat() + "Z"
            
            # Atributos OBD
            if groups[7]:
                position["attributes"]["odometer"] = int(groups[7])
            # Consumo instantáneo de combustible (groups[8]) no se utiliza
            if groups[9]:
                position["attributes"]["fuelConsumption"] = float(groups[9])
            if groups[10]:
                position["attributes"]["hours"] = int(groups[10])
            if groups[11]:
                position["attributes"]["obdSpeed"] = int(groups[11])
            if groups[12]:
                position["attributes"]["engineLoad"] = groups[12]
            if groups[13]:
                position["attributes"]["coolantTemp"] = int(groups[13])
            if groups[14]:
                position["attributes"]["throttle"] = groups[14]
            if groups[15]:
                position["attributes"]["rpm"] = int(groups[15])
            if groups[16]:
                position["attributes"]["battery"] = float(groups[16])
            if groups[17]:
                position["attributes"]["dtcs"] = groups[17].replace(',', ' ').strip()
                
        except (ValueError, IndexError) as e:
            print(f"Error al decodificar mensaje OBD: {e}")
            return None
            
        return position
    
    def decode_alternative(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Decodifica mensajes alternativos del protocolo GPS103"""
        match = self.PATTERN_ALT.match(sentence)
        if not match:
            return None
        
        groups = match.groups()
        imei = groups[0]
        
        position = {
            "protocol": "gps103",
            "deviceId": imei,
            "attributes": {}
        }
        
        try:
            # Evento y sensores
            if groups[1]:
                position["attributes"]["event"] = groups[1]
            if groups[2]:
                position["attributes"]["sensorId"] = groups[2]
            if groups[3]:
                position["attributes"]["sensorVoltage"] = float(groups[3])
                
            # Fecha y hora (formato HHmmss DDMMyy)
            hour = int(groups[4])
            minute = int(groups[5])
            second = int(groups[6])
            day = int(groups[7])
            month = int(groups[8])
            year = int(groups[9])
            
            dt = datetime.datetime(2000 + year if year < 100 else year, 
                                  month, day, hour, minute, second)
            position["deviceTime"] = dt.isoformat() + "Z"
            
            # RSSI
            if groups[10]:
                position["attributes"]["rssi"] = int(groups[10])
                
            # Estado GPS
            valid = int(groups[11]) > 0
            position["valid"] = valid
            
            # Coordenadas
            position["latitude"] = float(groups[12])
            position["longitude"] = float(groups[13])
            
            # Velocidad (convertir de km/h a nudos)
            if groups[14]:
                position["speed"] = float(groups[14]) * 0.539957
                
            # Curso y altitud
            if groups[15]:
                position["course"] = float(groups[15])
            if groups[16]:
                position["altitude"] = float(groups[16])
                
            # HDOP y satélites
            if groups[17]:
                position["attributes"]["hdop"] = float(groups[17])
            if groups[18]:
                position["attributes"]["satellites"] = int(groups[18])
                
            # Ignición y carga
            if groups[19]:
                position["attributes"]["ignition"] = groups[19] == "1"
            if groups[20]:
                position["attributes"]["charge"] = groups[20] == "1"
                
            # Error
            if groups[21]:
                position["attributes"]["error"] = groups[21]
                
        except (ValueError, IndexError) as e:
            print(f"Error al decodificar mensaje alternativo: {e}")
            return None
            
        return position
    
    def decode_photo(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Decodifica mensajes de foto del protocolo GPS103"""
        if len(sentence) < 24:
            return None
            
        imei = sentence[5:20]
        
        try:
            # Extraer datos hexadecimales
            data_hex = sentence[24:sentence.rindex(";") if sentence.endswith(";") else len(sentence)]
            data_bytes = binascii.unhexlify(data_hex)
            
            # Leer índice (similar a lo que hace el código Java)
            index = int.from_bytes(data_bytes[0:2], byteorder='little')
            
            # Agregar datos a la foto
            self.photo_data.extend(data_bytes[4:len(data_bytes)-2])
            
            # Si es el último paquete, crear posición
            if index + 1 >= self.photo_packets:
                position = {
                    "protocol": "gps103",
                    "deviceId": imei,
                    "attributes": {
                        "image": binascii.hexlify(self.photo_data).decode('ascii')
                    }
                }
                
                # Reiniciar datos de foto
                self.photo_packets = 0
                self.photo_data = bytearray()
                
                return position
                
        except Exception as e:
            print(f"Error al decodificar foto: {e}")
            self.photo_packets = 0
            self.photo_data = bytearray()
            
        return None
    
    def decode(self, sentence: str) -> Optional[Dict[str, Any]]:
        """
        Decodifica un mensaje del protocolo GPS103 a formato JSON
        
        Args:
            sentence: Mensaje del protocolo GPS103
            
        Returns:
            Un diccionario con los datos decodificados o None si no se pudo decodificar
        """
        if not sentence:
            return None
            
        # Manejo de mensajes de inicio
        if sentence.find("imei:") <= 30 and "imei:" in sentence:
            # En el código Java, responde con "LOAD"
            return None
            
        if sentence and sentence[0].isdigit():
            # En el código Java, responde con "ON"
            start = sentence.find("imei:")
            if start >= 0:
                sentence = sentence[start:]
            else:
                return None
                
        # Decodificar según el tipo de mensaje
        if len(sentence) > 21 and sentence[21:24].startswith("vr"):
            return self.decode_photo(sentence)
        elif len(sentence) > 21 and "OBD" in sentence[21:24]:
            return self.decode_obd(sentence)
        elif sentence.endswith("*"):
            return self.decode_alternative(sentence)
        else:
            return self.decode_regular(sentence)

def decode_gps103(message):
    decoder = Gps103Decoder()
    return decoder.decode(message)