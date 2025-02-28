import asyncio
import json
from src.ws.ws_manager import WebSocketManager
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.sender.position import update_position
from src.tcp.sender.events import send_event
from datetime import datetime


class TCPServer:
    def __init__(self, host="0.0.0.0", port=7005):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()

    async def tcp_to_json(self, port, data):
        if port == 6001:    # Coban
            return
            data_dict = decode_gps103(data)
        elif port == 6013:  # Sinotrack
            print(f"{port}: {data}")
            data_dict = decode_h02(data)
        elif port == 6027:  # Teltonika
            return
        else:
            return
        # Hilo de tratamiento de datos en segundo plano
        if data_dict["type"] == "position":
            devices = update_position(port, data_dict, self.ws_manager.devices)
            await self.ws_manager.save_devices(devices)
        elif data_dict["type"] == "event":
            users, data = await send_event(data_dict, self.ws_manager.devices)
        return

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        print(f"New TCP connection from {addr}")

        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                try:
                    received_json = json.loads(data.decode("utf-8"))
                    port = received_json["port"]
                    message_data = received_json["data"]
                    await self.tcp_to_json(port, message_data)
                except json.JSONDecodeError as e:
                    print(f"Receiver: Invalid JSON received: {e}")
                    print(f"Receiver: Raw data received: {data.decode('utf-8')}")
                except KeyError as e:
                    print(f"Receiver: Missing key in JSON: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"TCP server listening on port {self.port}")
        async with server:
            await server.serve_forever()
