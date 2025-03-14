import re
from datetime import datetime, timedelta


class Gps103Decoder:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.data = {}
        self.parts = self.raw_data.strip().rstrip(";").split(",")

    def parse(self):
        self.extract_imei()
        self.determine_event_type()
        self.parse_datetime()
        self.extract_gps_data()
        self.extract_additional_data()
        return self.classify_message()

    def extract_imei(self):
        if len(self.parts) > 0 and self.parts[0].startswith("imei:"):
            self.data["imei"] = self.parts[0].replace("imei:", "")
        else:
            self.data["imei"] = self.parts[0] if len(self.parts) > 0 else "unknown"

    def determine_event_type(self):
        if len(self.parts) > 1:
            command = self.parts[1]
            event_types = {
                "help me": "SOS alarm",
                "low battery": "low battery alarm",
                "move": "movement alarm",
                "speed": "deviceOverspeed",
                "stockade": "geo-fence alarm",
                "ac alarm": "power off alarm",
                "door alarm": "door alarm",
                "sensor alarm": "alarm",
                "acc alarm": "ACC alarm",
                "accident alarm": "accident alarm",
                "bonnet alarm": "bonnet alarm",
                "footbrake alarm": "footbrake alarm",
                "oil": "oil leak/oil theft alarm",
                "oil1": "oil 1 alarm",
                "oil2": "oil 2 alarm",
                "tracker": "position",
                "acc on": "ignitionOn",
                "acc off": "ignitionOff",
                "001": "real-time position",
                "101": "track upon time interval",
                "103": "track upon distance interval",
                "102": "cancel auto track continuously",
                "104": "cancel alarm",
                "105": "set movement alarm",
                "106": "cancel movement alarm",
                "107": "set overspeed alarm",
                "108": "set time zone",
                "109": "cut off oil and power",
                "110": "resume oil and power",
                "111": "arm",
                "112": "disarm",
                "113": "switch to SMS mode",
                "114": "set geo-fence",
                "115": "cancel geo-fence",
                "116": "data load",
                "117": "cancel upload",
                "118": "activate less GPRS mode",
                "119": "deactivate less GPRS mode",
                "120": "automatic update positions of vehicle turns",
                "121": "set multi-area management",
                "122": "set IP, port for address function",
                "123": "set shock alarm",
                "124": "cancel shock alarm",
                "125": "remote start",
                "126": "set OBDII data sending way",
                "150": "activate speed limit mode",
                "151": "deactivate speed limit mode",
                "152": "set speed limit",
                "160": "server request photo",
                "161": "server request photo retransmission",
                "170": "send LCD/handset, dispatch screen (notice) data",
                "171": "phone call dispatch: center sends answer race request to vehicles",
                "172": "phone call dispatch: center sends answer successfully to vehicle",
                "173": "phone call dispatch: center sends answer failed to vehicles",
                "174": "phone call dispatch: center sends cancel order to vehicle",
                "175": "driver hands in answer order",
                "176": "driver cancel order",
                "177": "driver finish task",
                "180": "send to LED ads screen, add ads information",
                "181": "delete ads",
                "TPMS": "tyre pressure monitoring",
                "rfid": "RFID",
            }

            if command.startswith("T:"):
                self.data["event_type"] = "temperature alarm"
                self.data["temperature"] = command.replace("T:", "")
            elif command.startswith("DTC"):
                self.data["event_type"] = "vehicle fault notification"
                self.data["dtc_code"] = command.replace("DTC", "")
            elif command.startswith("service"):
                self.data["event_type"] = "vehicle maintenance notification"
            else:
                self.data["event_type"] = event_types.get(command, "unknown")
        else:
            self.data["event_type"] = "unknown"

    def parse_datetime(self):
        if len(self.parts) > 2 and self.parts[2]:
            try:
                date_str = self.parts[2]
                if len(date_str) >= 12:  # Asegurarse de que la longitud sea suficiente
                    dt = datetime.strptime(date_str, "%y%m%d%H%M%S")
                    self.data["datetime"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    self.data["datetime"] = date_str
            except ValueError as e:
                self.data["datetime"] = self.parts[2]

    def extract_gps_data(self):
        if len(self.parts) > 5:
            for i in range(3, min(8, len(self.parts))):
                if self.parts[i] in ["A", "V"]:
                    self.data["gps_valid"] = True if self.parts[i] == "A" else False
                    if i + 3 < len(self.parts):
                        self.extract_coordinates(i + 1)
                    break

        for i, part in enumerate(self.parts):
            if (
                part == "F"
                and i + 2 < len(self.parts)
                and self.parts[i + 1].endswith(".000")
                and self.parts[i + 2] in ["A", "V"]
            ):
                if i + 5 < len(self.parts):
                    self.data["gps_time"] = self.parts[i + 1]
                    self.data["gps_valid"] = True if self.parts[i + 2] == "A" else False
                    self.extract_coordinates(i + 3)
                break

    def extract_coordinates(self, index):
        try:
            lat_str = self.parts[index]
            lat_dir = self.parts[index + 1]
            lat_deg = float(lat_str[:2])
            lat_min = float(lat_str[2:])
            lat_decimal = lat_deg + (lat_min / 60)
            if lat_dir == "S":
                lat_decimal = -lat_decimal
            self.data["latitude"] = round(lat_decimal, 6)

            lon_str = self.parts[index + 2]
            lon_dir = self.parts[index + 3]
            lon_deg = float(lon_str[:3])
            lon_min = float(lon_str[3:])
            lon_decimal = lon_deg + (lon_min / 60)
            if lon_dir == "W":
                lon_decimal = -lon_decimal
            self.data["longitude"] = round(lon_decimal, 6)

            if index + 4 < len(self.parts):
                try:
                    self.data["speed"] = float(self.parts[index + 4]) * 1.852
                except ValueError:
                    pass

            if index + 5 < len(self.parts):
                try:
                    self.data["course"] = float(self.parts[index + 5])
                except ValueError:
                    pass
        except Exception as e:
            print(f"Error parsing coordinates: {e}")

    def extract_additional_data(self):
        if "event_type" in self.data:
            if self.data["event_type"] == "real-time position":
                self.extract_position_data()
            elif self.data["event_type"] in [
                "SOS alarm",
                "low battery alarm",
                "movement alarm",
                "deviceOverspeed",
                "geo-fence alarm",
                "power off alarm",
                "door alarm",
                "alarm",
                "ACC alarm",
                "accident alarm",
                "bonnet alarm",
                "footbrake alarm",
                "temperature alarm",
                "oil leak/oil theft alarm",
                "vehicle fault notification",
                "vehicle maintenance notification",
            ]:
                self.extract_event_data()
            elif self.data["event_type"] == "tyre pressure monitoring":
                self.extract_tyre_pressure_data()
            elif self.data["event_type"] == "RFID":
                self.extract_rfid_data()

    def extract_position_data(self):
        if len(self.parts) > 11:
            self.data["direction"] = self.parts[11]
        if len(self.parts) > 12:
            self.data["altitude"] = self.parts[12]
        if len(self.parts) > 13:
            self.data["acc_status"] = self.parts[13]
        if len(self.parts) > 14:
            self.data["door_status"] = self.parts[14]
        if len(self.parts) > 15:
            self.data["oil_percentage_1"] = self.parts[15]
        if len(self.parts) > 16:
            self.data["oil_percentage_2"] = self.parts[16]
        if len(self.parts) > 17:
            self.data["temperature"] = self.parts[17]

    def extract_event_data(self):
        if self.data["event_type"] == "temperature alarm":
            self.data["temperature"] = self.parts[1]
        elif self.data["event_type"] == "oil leak/oil theft alarm":
            self.data["oil_percentage"] = self.parts[1]
        elif self.data["event_type"] == "vehicle fault notification":
            self.data["dtc_code"] = self.parts[1]
        elif self.data["event_type"] == "vehicle maintenance notification":
            self.data["maintenance_days"] = self.parts[1]
            self.data["maintenance_mileage"] = self.parts[2]

    def extract_tyre_pressure_data(self):
        if len(self.parts) > 3:
            self.data["tyre_status"] = self.parts[3]
        if len(self.parts) > 4:
            self.data["num_tyres"] = self.parts[4]
        if len(self.parts) > 5:
            self.data["left_front_pressure"] = self.parts[5]
        if len(self.parts) > 6:
            self.data["left_front_temperature"] = self.parts[6]
        if len(self.parts) > 7:
            self.data["left_front_status"] = self.parts[7]
        if len(self.parts) > 8:
            self.data["right_front_pressure"] = self.parts[8]
        if len(self.parts) > 9:
            self.data["right_front_temperature"] = self.parts[9]
        if len(self.parts) > 10:
            self.data["right_front_status"] = self.parts[10]
        if len(self.parts) > 11:
            self.data["left_rear_pressure"] = self.parts[11]
        if len(self.parts) > 12:
            self.data["left_rear_temperature"] = self.parts[12]
        if len(self.parts) > 13:
            self.data["left_rear_status"] = self.parts[13]
        if len(self.parts) > 14:
            self.data["right_rear_pressure"] = self.parts[14]
        if len(self.parts) > 15:
            self.data["right_rear_temperature"] = self.parts[15]
        if len(self.parts) > 16:
            self.data["right_rear_status"] = self.parts[16]

    def extract_rfid_data(self):
        if len(self.parts) > 3:
            self.data["rfid_tag"] = self.parts[3]

    def classify_message(self):
        if self.data["event_type"] in [
            "position",
            "track upon time interval",
            "track upon distance interval",
            "real-time position",
        ]:
            return {"type": "position", "data": self.data}
        else:
            return {"type": "event", "data": self.data}


def sumar_horas(fecha_str, horas):
    # Convertir la cadena a un objeto datetime
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
    
    # Sumar las horas
    nueva_fecha = fecha + timedelta(hours=horas)
    
    # Retornar la nueva fecha en formato de cadena
    return nueva_fecha.strftime('%Y-%m-%d %H:%M:%S')


def decode_gps103(raw_data):
    # decoder = Gps103Decoder(raw_data)
    # return decoder.parse()

    # Si el string está vacío o no contiene punto y coma, no hay expresiones válidas
    if not raw_data or ";" not in raw_data:
        return []

    # Dividir la cadena en múltiples expresiones
    expressions = []
    current = ""

    # Reconstruir correctamente las expresiones
    for char in raw_data:
        current += char
        if char == ";":
            expressions.append(current)
            current = ""

    # Si queda algo pendiente sin punto y coma, ignorarlo
    results = []

    # Mapeo de tipos de eventos
    event_type_map = {
        "acc on": "ignitionOn",
        "acc off": "ignitionOff",
        "help me": "sos",
        "low battery": "lowBattery",
        "move": "deviceMoving",
        "speed": "deviceOverspeed",
        "stockade": "geofenceAlarm",
        "ac alarm": "armAlarm",
        "acc alarm": "disarmAlarm",
        "door alarm": "doorAlarm",
        "sensor alarm": "alarm",
        "accident alarm": "accidentAlarm",
    }

    for expression in expressions:
        if not expression or not expression.endswith(";"):
            continue

        # Caso 1: Solo IMEI seguido de punto y coma (conexión simple)
        imei_pattern = r"^(\d+);$"
        imei_match = re.match(imei_pattern, expression)

        if imei_match:
            results.append(
                {
                    "type": "conexion",
                    "imei": imei_match.group(1),
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            continue

        # Caso 2: Conexión con formato especial (##,imei:IMEI,A;)
        special_conn_pattern = r".*?imei:(\d+),.*?;$"
        special_conn_match = re.match(special_conn_pattern, expression)

        if (
            special_conn_match
            and "tracker" not in expression
            and not any(event in expression for event in event_type_map)
        ):
            results.append({"type": "conexion", "imei": special_conn_match.group(1), "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            continue

        # Caso 3: Eventos
        event_pattern = (
            r"imei:(\d+),(.*?),(\d{12}).*?,A,(\d+\.\d+),([NS]),(\d+\.\d+),([EW]).*?;$"
        )
        event_match = re.match(event_pattern, expression)

        if event_match and any(
            event in event_match.group(2) for event in event_type_map
        ):
            imei, event_text, datetime_str, lat, lat_dir, lon, lon_dir = (
                event_match.groups()
            )

            # Determinar el tipo de evento
            event_type = event_text
            for key in event_type_map:
                if key in event_text:
                    event_type = event_type_map[key]
                    break

            # Formatear datetime
            if len(datetime_str) == 12:
                formatted_datetime = f"20{datetime_str[0:2]}-{datetime_str[2:4]}-{datetime_str[4:6]} {datetime_str[6:8]}:{datetime_str[8:10]}:{datetime_str[10:12]}"
            else:
                # Si el formato es diferente (como 0809231929)
                formatted_datetime = f"20{datetime_str[0:2]}-{datetime_str[2:4]}-{datetime_str[4:6]} {datetime_str[6:8]}:{datetime_str[8:10]}:{datetime_str[10:12]}"

            # Procesar latitud
            lat_degrees = float(lat[:2])
            lat_minutes = float(lat[2:])
            latitude = lat_degrees + (lat_minutes / 60)
            if lat_dir == "S":
                latitude = -latitude

            # Procesar longitud
            lon_degrees = float(lon[:3])
            lon_minutes = float(lon[3:])
            longitude = lon_degrees + (lon_minutes / 60)
            if lon_dir == "W":
                longitude = -longitude

            results.append(
                {
                    "type": "event",
                    "event_type": event_type,
                    "imei": imei,
                    "datetime": sumar_horas(formatted_datetime, 5),
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )
            continue

        # Caso 4: Posición completa (tracker)
        position_pattern = (
            r"imei:(\d+),tracker,(\d{12}).*?,A,(\d+\.\d+),([NS]),(\d+\.\d+),([EW]).*?;$"
        )
        position_match = re.match(position_pattern, expression)

        if position_match:
            imei, datetime_str, lat, lat_dir, lon, lon_dir = position_match.groups()

            # Formatear datetime
            formatted_datetime = f"20{datetime_str[0:2]}-{datetime_str[2:4]}-{datetime_str[4:6]} {datetime_str[6:8]}:{datetime_str[8:10]}:{datetime_str[10:12]}"

            # Procesar latitud
            lat_degrees = float(lat[:2])
            lat_minutes = float(lat[2:])
            latitude = lat_degrees + (lat_minutes / 60)
            if lat_dir == "S":
                latitude = -latitude

            # Procesar longitud
            lon_degrees = float(lon[:3])
            lon_minutes = float(lon[3:])
            longitude = lon_degrees + (lon_minutes / 60)
            if lon_dir == "W":
                longitude = -longitude

            # Extraer velocidad y rumbo si están presentes
            speed = 0.0
            course = 0.0

            speed_course_pattern = r",[EW],(\d+\.\d+),(\d+\.\d+)"
            speed_course_match = re.search(speed_course_pattern, expression)
            if speed_course_match:
                speed = float(speed_course_match.group(1)) * 1.852 # Convertir de nudos a km/h
                course = float(speed_course_match.group(2))

            results.append(
                {
                    "type": "position",
                    "imei": imei,
                    "datetime": sumar_horas(formatted_datetime, 5),
                    "latitude": latitude,
                    "longitude": longitude,
                    "speed": speed,
                    "course": course,
                }
            )

    return results
