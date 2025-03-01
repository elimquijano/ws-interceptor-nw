import asyncio
import json
from src.ws.ws_manager import WebSocketManager
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.sender.position import update_position
from src.tcp.sender.events import get_users_and_process_data, send_notificacion
from datetime import datetime


class TCPServer:
    def __init__(self, host="0.0.0.0", port=7005):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()

    async def process_data(self, port, data, devices):
        if data["type"] == "position":
            devices = update_position(port, data, self.ws_manager.devices)
            if devices is not None:
                await self.ws_manager.save_devices(devices)
        elif data["type"] == "event" and data["data"]["event_type"] != "unknown":
            result = await get_users_and_process_data(
                port, data, self.ws_manager.devices
            )
            if result is not None:
                users = result["users"]
                event_data = result["process_data"]
                asyncio.create_task(send_notificacion(users, event_data))
                asyncio.create_task(self.ws_manager.send_events(users, event_data))
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Evento enviado")

    async def tcp_to_json(self, port, data):
        print(f"{port} - {data}")
        if port == 6001:  # Coban
            data_dict = decode_gps103(data)
        elif port == 6013:  # Sinotrack
            data_dict = decode_h02(data)
        elif port == 6027:  # Teltonika
            return
        else:
            return

        # Iniciar el procesamiento de datos en segundo plano
        asyncio.create_task(self.process_data(port, data_dict, self.ws_manager.devices))

        # Retornar inmediatamente para indicar que la ejecución ha terminado
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
