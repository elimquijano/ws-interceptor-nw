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


def decode_h02(message):
    decoder = H02ProtocolDecoder(message)
    return decoder.parse()
