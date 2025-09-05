"""
Teltonika Protocol Decoder for Python
Handles TCP and UDP connections on port 6027
Decodes Teltonika GPS tracker data packets
"""

import struct
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TeltonikaDecoder:
    # Codec constants
    CODEC_GH3000 = 0x07
    CODEC_8 = 0x08
    CODEC_8_EXT = 0x8E
    CODEC_12 = 0x0C
    CODEC_13 = 0x0D
    CODEC_16 = 0x10

    # Parameter definitions for different device models
    FMB_MODELS = {
        "FMB001",
        "FMC001",
        "FMB010",
        "FMB002",
        "FMB020",
        "FMB003",
        "FMB110",
        "FMB120",
        "FMB122",
        "FMB125",
        "FMB130",
        "FMB140",
        "FMU125",
        "FMB900",
        "FMB920",
        "FMB962",
        "FMB964",
        "FM3001",
        "FMB202",
        "FMB204",
        "FMB206",
        "FMT100",
        "MTB100",
        "FMP100",
        "MSP500",
        "FMC125",
        "FMM125",
        "FMU130",
        "FMC130",
        "FMM130",
        "FMB150",
        "FMC150",
        "FMM150",
        "FMC920",
    }

    FMC_MODELS = {"FMC640", "FMC650", "FMM640"}

    def __init__(self):
        self.device_sessions = {}  # Store device sessions
        self.photos = {}  # Store incomplete photo data

        # Parameter handlers mapping
        self.parameter_handlers = self._init_parameter_handlers()

    def _init_parameter_handlers(self) -> Dict[int, Dict]:
        """Initialize parameter handlers for different IO elements"""
        handlers = {}

        # Digital inputs
        handlers[1] = {"handler": self._handle_digital_input, "name": "din1"}
        handlers[2] = {"handler": self._handle_digital_input, "name": "din2"}
        handlers[3] = {"handler": self._handle_digital_input, "name": "din3"}
        handlers[4] = {"handler": self._handle_digital_input, "name": "din4"}

        # Analog inputs
        handlers[9] = {
            "handler": self._handle_analog_input,
            "name": "adc1",
            "scale": 0.001,
        }
        handlers[10] = {
            "handler": self._handle_analog_input,
            "name": "adc2",
            "scale": 0.001,
        }

        # System parameters
        handlers[11] = {"handler": self._handle_iccid, "name": "iccid"}
        handlers[16] = {"handler": self._handle_odometer, "name": "odometer"}
        handlers[21] = {"handler": self._handle_rssi, "name": "rssi"}
        handlers[66] = {"handler": self._handle_power, "name": "power", "scale": 0.001}
        handlers[67] = {
            "handler": self._handle_battery,
            "name": "battery",
            "scale": 0.001,
        }

        # Engine parameters
        handlers[31] = {"handler": self._handle_engine_load, "name": "engine_load"}
        handlers[32] = {"handler": self._handle_coolant_temp, "name": "coolant_temp"}
        handlers[36] = {"handler": self._handle_rpm, "name": "rpm"}
        handlers[81] = {"handler": self._handle_obd_speed, "name": "obd_speed"}
        handlers[82] = {"handler": self._handle_throttle, "name": "throttle"}
        handlers[84] = {
            "handler": self._handle_fuel_level,
            "name": "fuel_level",
            "scale": 0.1,
        }
        handlers[85] = {"handler": self._handle_rpm, "name": "obd_rpm"}

        # Status flags
        handlers[239] = {"handler": self._handle_ignition, "name": "ignition"}
        handlers[240] = {"handler": self._handle_movement, "name": "movement"}
        handlers[241] = {"handler": self._handle_operator, "name": "operator"}

        # Alarms
        handlers[246] = {"handler": self._handle_tow_alarm, "name": "tow_alarm"}
        handlers[247] = {"handler": self._handle_crash_alarm, "name": "crash_alarm"}
        handlers[249] = {"handler": self._handle_jamming_alarm, "name": "jamming_alarm"}
        handlers[251] = {"handler": self._handle_idle_alarm, "name": "idle_alarm"}
        handlers[252] = {
            "handler": self._handle_power_cut_alarm,
            "name": "power_cut_alarm",
        }
        handlers[253] = {
            "handler": self._handle_harsh_behavior,
            "name": "harsh_behavior",
        }

        # Temperature sensors
        handlers[72] = {
            "handler": self._handle_temperature,
            "name": "temp1",
            "scale": 0.1,
        }
        handlers[73] = {
            "handler": self._handle_temperature,
            "name": "temp2",
            "scale": 0.1,
        }
        handlers[74] = {
            "handler": self._handle_temperature,
            "name": "temp3",
            "scale": 0.1,
        }
        handlers[75] = {
            "handler": self._handle_temperature,
            "name": "temp4",
            "scale": 0.1,
        }

        return handlers

    def _handle_digital_input(self, value: int, **kwargs) -> bool:
        return value > 0

    def _handle_analog_input(self, value: int, scale: float = 1.0, **kwargs) -> float:
        return value * scale

    def _handle_iccid(self, value: int, **kwargs) -> str:
        return str(value)

    def _handle_odometer(self, value: int, **kwargs) -> int:
        return value

    def _handle_rssi(self, value: int, **kwargs) -> int:
        return value

    def _handle_power(self, value: int, scale: float = 1.0, **kwargs) -> float:
        return value * scale

    def _handle_battery(self, value: int, scale: float = 1.0, **kwargs) -> float:
        return value * scale

    def _handle_engine_load(self, value: int, **kwargs) -> int:
        return value

    def _handle_coolant_temp(self, value: int, **kwargs) -> int:
        return struct.unpack("b", struct.pack("B", value))[0]  # signed byte

    def _handle_rpm(self, value: int, **kwargs) -> int:
        return value

    def _handle_obd_speed(self, value: int, **kwargs) -> int:
        return value

    def _handle_throttle(self, value: int, **kwargs) -> int:
        return value

    def _handle_fuel_level(self, value: int, scale: float = 1.0, **kwargs) -> float:
        return value * scale

    def _handle_ignition(self, value: int, **kwargs) -> bool:
        return value > 0

    def _handle_movement(self, value: int, **kwargs) -> bool:
        return value > 0

    def _handle_operator(self, value: int, **kwargs) -> int:
        return value

    def _handle_tow_alarm(self, value: int, **kwargs) -> Optional[str]:
        return "tow" if value > 0 else None

    def _handle_crash_alarm(self, value: int, **kwargs) -> Optional[str]:
        return "crash" if value > 0 else None

    def _handle_jamming_alarm(self, value: int, **kwargs) -> Optional[str]:
        return "jamming" if value > 0 else None

    def _handle_idle_alarm(self, value: int, **kwargs) -> Optional[str]:
        return "idle" if value > 0 else None

    def _handle_power_cut_alarm(self, value: int, **kwargs) -> Optional[str]:
        return "power_cut" if value > 0 else None

    def _handle_harsh_behavior(self, value: int, **kwargs) -> Optional[str]:
        behavior_map = {1: "acceleration", 2: "braking", 3: "cornering"}
        return behavior_map.get(value)

    def _handle_temperature(self, value: int, scale: float = 1.0, **kwargs) -> float:
        return struct.unpack("i", struct.pack("I", value))[0] * scale  # signed int

    def _read_value(self, data: bytes, offset: int, length: int) -> Tuple[int, int]:
        """Read value of specified length from data at offset"""
        if length == 1:
            value = struct.unpack_from("B", data, offset)[0]
        elif length == 2:
            value = struct.unpack_from(">H", data, offset)[0]
        elif length == 4:
            value = struct.unpack_from(">I", data, offset)[0]
        elif length == 8:
            value = struct.unpack_from(">Q", data, offset)[0]
        else:
            raise ValueError(f"Unsupported value length: {length}")

        return value, offset + length

    def _decode_parameter(
        self, param_id: int, value: int, length: int, position: Dict
    ) -> None:
        """Decode a single parameter and add it to position data"""
        if param_id in self.parameter_handlers:
            handler_info = self.parameter_handlers[param_id]
            handler = handler_info["handler"]
            name = handler_info["name"]

            try:
                decoded_value = handler(value, **handler_info)
                if decoded_value is not None:
                    if name.endswith("_alarm") and decoded_value:
                        if "alarms" not in position:
                            position["alarms"] = []
                        position["alarms"].append(decoded_value)
                    else:
                        position[name] = decoded_value
            except Exception as e:
                logger.warning(f"Error decoding parameter {param_id}: {e}")
                position[f"io_{param_id}"] = value
        else:
            # Unknown parameter, store as generic IO
            position[f"io_{param_id}"] = value

    def _decode_location(
        self, data: bytes, offset: int, codec: int
    ) -> Tuple[Dict, int]:
        """Decode location data from AVL record"""
        position = {}

        if codec == self.CODEC_GH3000:
            # GH3000 codec handling (simplified)
            timestamp, offset = self._read_value(data, offset, 4)
            timestamp &= 0x3FFFFFFF
            timestamp += 1167609600  # 2007-01-01 00:00:00
            position["timestamp"] = datetime.fromtimestamp(timestamp)

            global_mask, offset = self._read_value(data, offset, 1)

            if global_mask & 0x01:  # Location data present
                location_mask, offset = self._read_value(data, offset, 1)

                if location_mask & 0x01:  # Coordinates
                    lat = struct.unpack_from(">f", data, offset)[0]
                    offset += 4
                    lon = struct.unpack_from(">f", data, offset)[0]
                    offset += 4
                    position["latitude"] = lat
                    position["longitude"] = lon

                if location_mask & 0x02:  # Altitude
                    altitude, offset = self._read_value(data, offset, 2)
                    position["altitude"] = altitude

                if location_mask & 0x04:  # Course
                    course, offset = self._read_value(data, offset, 1)
                    position["course"] = course * 360.0 / 256

                if location_mask & 0x08:  # Speed
                    speed, offset = self._read_value(data, offset, 1)
                    position["speed"] = speed * 1.852  # Convert to km/h

                if location_mask & 0x10:  # Satellites
                    satellites, offset = self._read_value(data, offset, 1)
                    position["satellites"] = satellites
            else:
                position["timestamp"] = datetime.fromtimestamp(timestamp)
                position["valid"] = False

        else:  # Standard codecs (8, 8_EXT, 16, etc.)
            # Timestamp (8 bytes)
            timestamp, offset = self._read_value(data, offset, 8)
            position["timestamp"] = datetime.fromtimestamp(timestamp / 1000.0)

            # Priority
            priority, offset = self._read_value(data, offset, 1)
            position["priority"] = priority

            # GPS data
            longitude, offset = self._read_value(data, offset, 4)
            position["longitude"] = (
                struct.unpack(">i", struct.pack(">I", longitude))[0] / 10000000.0
            )

            latitude, offset = self._read_value(data, offset, 4)
            position["latitude"] = (
                struct.unpack(">i", struct.pack(">I", latitude))[0] / 10000000.0
            )

            altitude, offset = self._read_value(data, offset, 2)
            position["altitude"] = struct.unpack(">h", struct.pack(">H", altitude))[0]

            course, offset = self._read_value(data, offset, 2)
            position["course"] = course

            satellites, offset = self._read_value(data, offset, 1)
            position["satellites"] = satellites
            position["valid"] = satellites > 0

            speed, offset = self._read_value(data, offset, 2)
            position["speed"] = speed * 1.852  # Convert to km/h

            # Event ID
            if codec in [self.CODEC_8_EXT, self.CODEC_16]:
                event_id, offset = self._read_value(data, offset, 2)
            else:
                event_id, offset = self._read_value(data, offset, 1)
            position["event_id"] = event_id

            if codec == self.CODEC_16:
                generation_type, offset = self._read_value(data, offset, 1)
                position["generation_type"] = generation_type

            # Total IO data records
            if codec == self.CODEC_8_EXT:
                total_io, offset = self._read_value(data, offset, 2)
            else:
                total_io, offset = self._read_value(data, offset, 1)

        # Decode IO elements
        global_mask = 0x0F if codec != self.CODEC_GH3000 else global_mask

        # 1-byte IO elements
        if global_mask & 0x02:
            if codec == self.CODEC_8_EXT:
                count, offset = self._read_value(data, offset, 2)
            else:
                count, offset = self._read_value(data, offset, 1)

            for _ in range(count):
                if codec in [self.CODEC_8_EXT, self.CODEC_16]:
                    param_id, offset = self._read_value(data, offset, 2)
                else:
                    param_id, offset = self._read_value(data, offset, 1)

                value, offset = self._read_value(data, offset, 1)
                self._decode_parameter(param_id, value, 1, position)

        # 2-byte IO elements
        if global_mask & 0x04:
            if codec == self.CODEC_8_EXT:
                count, offset = self._read_value(data, offset, 2)
            else:
                count, offset = self._read_value(data, offset, 1)

            for _ in range(count):
                if codec in [self.CODEC_8_EXT, self.CODEC_16]:
                    param_id, offset = self._read_value(data, offset, 2)
                else:
                    param_id, offset = self._read_value(data, offset, 1)

                value, offset = self._read_value(data, offset, 2)
                self._decode_parameter(param_id, value, 2, position)

        # 4-byte IO elements
        if global_mask & 0x08:
            if codec == self.CODEC_8_EXT:
                count, offset = self._read_value(data, offset, 2)
            else:
                count, offset = self._read_value(data, offset, 1)

            for _ in range(count):
                if codec in [self.CODEC_8_EXT, self.CODEC_16]:
                    param_id, offset = self._read_value(data, offset, 2)
                else:
                    param_id, offset = self._read_value(data, offset, 1)

                value, offset = self._read_value(data, offset, 4)
                self._decode_parameter(param_id, value, 4, position)

        # 8-byte IO elements
        if codec in [self.CODEC_8, self.CODEC_8_EXT, self.CODEC_16]:
            if codec == self.CODEC_8_EXT:
                count, offset = self._read_value(data, offset, 2)
            else:
                count, offset = self._read_value(data, offset, 1)

            for _ in range(count):
                if codec in [self.CODEC_8_EXT, self.CODEC_16]:
                    param_id, offset = self._read_value(data, offset, 2)
                else:
                    param_id, offset = self._read_value(data, offset, 1)

                value, offset = self._read_value(data, offset, 8)
                self._decode_parameter(param_id, value, 8, position)

        return position, offset

    def decode_tcp_packet(self, data: bytes) -> List[Dict]:
        """Decode TCP packet data"""
        if len(data) == 1 and data[0] == 0xFF:
            return []

        offset = 0

        # Check if this is identification packet
        if len(data) >= 2:
            imei_length = struct.unpack_from(">H", data, offset)[0]
            if imei_length > 0 and imei_length < len(data):
                # This is identification
                offset += 2
                imei = data[offset : offset + imei_length].decode("ascii")
                logger.info(f"Device identification: {imei}")
                return [{"type": "identification", "imei": imei}]

        # Skip preamble (4 bytes of zeros)
        offset = 4

        # Data length
        data_length = struct.unpack_from(">I", data, offset)[0]
        offset += 4

        # Codec ID
        codec = struct.unpack_from("B", data, offset)[0]
        offset += 1

        # Number of records
        record_count = struct.unpack_from("B", data, offset)[0]
        offset += 1

        positions = []

        for i in range(record_count):
            try:
                position, offset = self._decode_location(data, offset, codec)
                position["codec"] = codec
                position["record_number"] = i + 1
                positions.append(position)
            except Exception as e:
                logger.error(f"Error decoding record {i + 1}: {e}")
                break

        return positions

    def decode_udp_packet(self, data: bytes) -> List[Dict]:
        """Decode UDP packet data"""
        offset = 0

        # Length
        length = struct.unpack_from(">H", data, offset)[0]
        offset += 2

        # Packet ID
        packet_id = struct.unpack_from(">H", data, offset)[0]
        offset += 2

        # Packet type
        packet_type = struct.unpack_from("B", data, offset)[0]
        offset += 1

        # Location packet ID
        location_packet_id = struct.unpack_from("B", data, offset)[0]
        offset += 1

        # IMEI length
        imei_length = struct.unpack_from(">H", data, offset)[0]
        offset += 2

        # IMEI
        imei = data[offset : offset + imei_length].decode("ascii")
        offset += imei_length

        # Codec
        codec = struct.unpack_from("B", data, offset)[0]
        offset += 1

        # Number of records
        record_count = struct.unpack_from("B", data, offset)[0]
        offset += 1

        positions = []

        for i in range(record_count):
            try:
                position, offset = self._decode_location(data, offset, codec)
                position["codec"] = codec
                position["imei"] = imei
                position["packet_id"] = packet_id
                position["location_packet_id"] = location_packet_id
                position["record_number"] = i + 1
                positions.append(position)
            except Exception as e:
                logger.error(f"Error decoding UDP record {i + 1}: {e}")
                break

        return positions


def decode_teltonika(data: bytes, conn_type: str) -> dict:
    decoder = TeltonikaDecoder()
    if conn_type == "tcp":
        # Decode packet
        positions = decoder.decode_tcp_packet(data)

        if positions:
            for pos in positions:
                if pos.get("type") == "identification":
                    logger.info(f"Decode conexion: {pos}")
                    return []
                else:
                    logger.info(f"Decoded position: {pos}")
                    return []
    elif conn_type == "udp":
        # Decode packet
        positions = decoder.decode_udp_packet(data)

        if positions:
            for pos in positions:
                logger.info(f"Decoded UDP position: {pos}")
                return []

    else:
        return []
