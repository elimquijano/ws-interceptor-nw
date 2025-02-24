from datetime import datetime

class Gps103Decoder:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.data = {}
        self.parts = self.raw_data.strip().split(",")

    def parse(self):
        self.extract_imei()
        self.determine_event_type()
        self.parse_datetime()
        self.extract_gps_data()
        return self.data

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
                "sensor alarm": "shock sensor alarm",
                "acc alarm": "ACC alarm",
                "accident alarm": "accident alarm",
                "bonnet alarm": "bonnet alarm",
                "footbrake alarm": "footbrake alarm",
                "oil": "oil leak/oil theft alarm",
                "oil1": "oil 1 alarm",
                "oil2": "oil 2 alarm",
                "001": "location information",
                "101": "track upon time interval",
                "103": "track upon distance interval",
            }

            if command.startswith("T:"):
                self.data["event_type"] = "temperature alarm"
                self.data["temperature"] = command.replace("T:", "")
            else:
                self.data["event_type"] = event_types.get(command, "unknown")
        else:
            self.data["event_type"] = "unknown"

    def parse_datetime(self):
        if len(self.parts) > 2 and self.parts[2]:
            try:
                date_str = self.parts[2]
                if len(date_str) >= 10:
                    dt = datetime.strptime(date_str, "%d%m%y%H%M")
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
            if part == "F" and i + 2 < len(self.parts) and self.parts[i + 1].endswith(".000") and self.parts[i + 2] in ["A", "V"]:
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
        except Exception as e:
            print(f"Error parsing coordinates: {e}")

def decode_gps103(message):
    decoder = Gps103Decoder(message)
    return decoder.parse()