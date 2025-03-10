import re
from datetime import datetime


class H02ProtocolDecoder:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.data = {}
        self.parts = self.raw_data.strip().split(",")

    def parse(self):
        self.determine_event_type()
        self.extract_data()
        return self.data

    def determine_event_type(self):
        command = self.parts[2]
        event_types = {
            "V1": "position",
            "XT": "heartbeat packet",
            "VI1": "location request",
            "BC": "blind spots uploading",
            "ALRM": "device alarm",
            "S20": "cut-off oil & engine/recovery oil & engine",
            "CR": "response to location request",
            "SF": "fortification",
            "SF2": "fortification version II",
            "CF": "disarming",
            "CF2": "disarming version II",
            "UR": "main number bind",
            "IP": "server setting",
            "MP": "terminal password setting",
            "XT/NXT": "interval setting",
            "KC": "alarm setting",
            "CQ": "device reboot",
            "RESET": "reset to defaults",
            "APN": "network access point",
            "ACPC": "answer mode",
            "SIMEI": "IMEI setting",
            "SLAN": "language setting",
            "CALB": "audio monitor",
            "PWM": "power saving mode setting",
            "INFO": "query device information",
        }
        self.data["type"] = event_types.get(command, "unknown")

    def extract_data(self):
        event_type = self.data["type"]
        if event_type in [
            "position",
            "location request",
            "blind spots uploading",
            "device alarm",
        ]:
            self.data["data"] = self.extract_location_data()
        elif event_type == "heartbeat packet":
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type == "cut-off oil & engine/recovery oil & engine":
            self.data["data"] = self.extract_cut_off_recovery_data()
        elif event_type == "response to location request":
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type in ["fortification", "fortification version II"]:
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type in ["disarming", "disarming version II"]:
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type == "main number bind":
            self.data["data"] = {"imei": self.parts[1], "num_list": self.parts[3]}
        elif event_type == "server setting":
            self.data["data"] = self.extract_server_setting_data()
        elif event_type == "terminal password setting":
            self.data["data"] = self.extract_terminal_password_data()
        elif event_type == "interval setting":
            self.data["data"] = {"imei": self.parts[1], "interval": self.parts[3]}
        elif event_type == "alarm setting":
            self.data["data"] = {
                "imei": self.parts[1],
                "key": self.parts[3],
                "type": self.parts[4],
            }
        elif event_type == "device reboot":
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type == "reset to defaults":
            self.data["data"] = self.extract_reset_to_defaults_data()
        elif event_type == "network access point":
            self.data["data"] = self.extract_network_access_point_data()
        elif event_type == "answer mode":
            self.data["data"] = {"imei": self.parts[1], "operation": self.parts[3]}
        elif event_type == "IMEI setting":
            self.data["data"] = self.extract_imei_setting_data()
        elif event_type == "language setting":
            self.data["data"] = self.extract_language_setting_data()
        elif event_type == "audio monitor":
            self.data["data"] = self.extract_audio_monitor_data()
        elif event_type == "power saving mode setting":
            self.data["data"] = {"imei": self.parts[1]}
        elif event_type == "query device information":
            self.data["data"] = {"imei": self.parts[1]}
        else:
            self.data["data"] = {}

    def extract_location_data(self):
        lat_str = self.parts[5]
        lon_str = self.parts[7]
        lat_deg = float(lat_str[:2])
        lat_min = float(lat_str[2:])
        lon_deg = float(lon_str[:3])
        lon_min = float(lon_str[3:])

        latitude = lat_deg + (lat_min / 60)
        longitude = lon_deg + (lon_min / 60)

        return {
            "imei": self.parts[1],
            "event_type": "position",
            "data_valid_bit": self.parts[4],
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "speed": float(self.parts[9]) * 1.852,  # Convertir de nudos a km/h
            "course": float(self.parts[10]),
            "datetime": f"{datetime.strptime(self.parts[11], '%d%m%y').strftime('%Y-%m-%d')} {datetime.strptime(self.parts[3], '%H%M%S').strftime('%H:%M:%S')}",
            "vehicle_status": self.parts[12],
            "power_capacity": self.parts[13],
        }

    def extract_cut_off_recovery_data(self):
        return {
            "imei": self.parts[1],
            "time": datetime.strptime(self.parts[3], "%H%M%S").strftime("%H:%M:%S"),
            "ultimate_power_mode": self.parts[4],
            "cut_off_or_recovery": self.parts[5],
        }

    def extract_server_setting_data(self):
        return {
            "imei": self.parts[1],
            "index": self.parts[3],
            "ip": self.parts[4],
            "port": self.parts[5],
            "domain": self.parts[6],
            "time": datetime.strptime(self.parts[7], "%H%M%S").strftime("%H:%M:%S"),
        }

    def extract_terminal_password_data(self):
        return {
            "imei": self.parts[1],
            "old_password": self.parts[3],
            "new_password": self.parts[4],
        }

    def extract_reset_to_defaults_data(self):
        return {
            "imei": self.parts[1],
            "time": datetime.strptime(self.parts[3], "%H%M%S").strftime("%H:%M:%S"),
        }

    def extract_network_access_point_data(self):
        return {
            "imei": self.parts[1],
            "name": self.parts[3],
            "user": self.parts[4],
            "pwd": self.parts[5],
        }

    def extract_imei_setting_data(self):
        return {
            "imei": self.parts[1],
            "new_imei": self.parts[3],
            "time": datetime.strptime(self.parts[4], "%H%M%S").strftime("%H:%M:%S"),
        }

    def extract_language_setting_data(self):
        return {
            "imei": self.parts[1],
            "language": self.parts[3],
            "time": datetime.strptime(self.parts[4], "%H%M%S").strftime("%H:%M:%S"),
        }

    def extract_audio_monitor_data(self):
        return {
            "imei": self.parts[1],
            "time": datetime.strptime(self.parts[3], "%H%M%S").strftime("%H:%M:%S"),
        }


def decode_h02(full_string):
    # decoder = H02ProtocolDecoder(full_string)
    # return decoder.parse()

    results = []

    # Dividir la cadena en mensajes individuales
    # Usamos una expresión regular para encontrar todos los mensajes que terminan con #
    messages = re.findall(r"(?:\*?HQ,[^#]+#)", full_string)

    for raw_message in messages:
        # Verificar si el mensaje tiene el formato correcto
        if not (
            raw_message.startswith("*HQ,") or raw_message.startswith("HQ,")
        ) or not raw_message.endswith("#"):
            print({"error": "Formato de mensaje inválido", "raw": raw_message})
            continue

        # Normalizar el mensaje (asegurar que comience con *HQ)
        if raw_message.startswith("HQ,"):
            raw_message = "*" + raw_message

        # Caso 1: Mensaje de conexión (*HQ,numero,V4,V1,numero#)
        connection_pattern = r"\*HQ,(\d+),V4,V1,(\d+)#"
        connection_match = re.match(connection_pattern, raw_message)

        if connection_match:
            imei = connection_match.group(1)
            datetime_str = connection_match.group(2)

            # Formatear la fecha y hora (asumiendo formato YYYYMMDDhhmmss)
            formatted_datetime = None
            if len(datetime_str) == 14:
                try:
                    dt = datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
                    formatted_datetime = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_datetime = datetime_str

            result = {
                "type": "conexion",
                "imei": imei,
                "datetime": formatted_datetime or datetime_str,
            }
            results.append(result)
            continue

        # Caso 2: Mensaje de posición (*HQ,imei,V1,time,A,lat,S,lon,W,speed,course,date,...)
        position_pattern = r"\*HQ,(\d+),V1,(\d{6}),A,([\d\.]+),(N|S),([\d\.]+),(E|W),([\d\.]+),(\d+),(\d{6})"
        position_match = re.search(position_pattern, raw_message)

        if position_match:
            imei = position_match.group(1)
            time_str = position_match.group(2)
            lat_raw = position_match.group(3)
            lat_dir = position_match.group(4)
            lon_raw = position_match.group(5)
            lon_dir = position_match.group(6)
            speed = position_match.group(7)
            course = position_match.group(8)
            date_str = position_match.group(9)

            # Formatear la hora (hhmmss -> hh:mm:ss)
            formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"

            # Formatear la fecha (ddmmyy -> yyyy-mm-dd)
            day = date_str[:2]
            month = date_str[2:4]
            year = "20" + date_str[4:6]
            formatted_date = f"{year}-{month}-{day}"

            # Formatear fecha y hora completa
            formatted_datetime = f"{formatted_date} {formatted_time}"

            # Procesar la latitud
            lat_degrees = float(lat_raw[:2])
            lat_minutes = float(lat_raw[2:])
            latitude = lat_degrees + (lat_minutes / 60.0)
            if lat_dir == "S":
                latitude = -latitude

            # Procesar la longitud
            lon_degrees = float(lon_raw[:3])
            lon_minutes = float(lon_raw[3:])
            longitude = lon_degrees + (lon_minutes / 60.0)
            if lon_dir == "W":
                longitude = -longitude

            result = {
                "type": "position",
                "imei": imei,
                "datetime": formatted_datetime,
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "speed": float(speed) * 1.852, # Convertir de nudos a km/h
                "course": float(course),
            }
            results.append(result)
            continue

        # Si no coincide con ninguno de los patrones conocidos
        print({"error": "Formato de mensaje no reconocido", "raw": raw_message})

    return results
