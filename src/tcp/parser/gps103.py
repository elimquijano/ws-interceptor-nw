from datetime import datetime


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
                "speed": "over speed alarm",
                "stockade": "geo-fence alarm",
                "ac alarm": "power off alarm",
                "door alarm": "door alarm",
                "sensor alarm": "shock alarm",
                "acc alarm": "ACC alarm",
                "accident alarm": "accident alarm",
                "bonnet alarm": "bonnet alarm",
                "footbrake alarm": "footbrake alarm",
                "oil": "oil leak/oil theft alarm",
                "oil1": "oil 1 alarm",
                "oil2": "oil 2 alarm",
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
                "tracker": "position",
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
                    self.data["speed"] = float(self.parts[index + 4])
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
                "over speed alarm",
                "geo-fence alarm",
                "power off alarm",
                "door alarm",
                "shock alarm",
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


def decode_gps103(message):
    decoder = Gps103Decoder(message)
    return decoder.parse()
