import asyncio
import json
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.sender.position import Position
from src.tcp.sender.events import Events


class TCPServer:
    def __init__(self, host="0.0.0.0", port=7005):
        self.host = host
        self.port = port

    async def process_data(self, port, data):
        if data["type"] == "conexion":
            p = Position()
            asyncio.create_task(p.update_lastupdate(port, data))
        elif data["type"] == "position":
            p = Position()
            asyncio.create_task(p.update_position(port, data))
        elif data["type"] == "event" and data["event_type"] != "unknown":
            e = Events()
            asyncio.create_task(e.send_events_to_users(port, data))

    async def tcp_to_json(self, port, data):
        print(f"{port} - {data}")
        if port == 6001:  # Coban
            data_array = decode_gps103(data)
        elif port == 6013:  # Sinotrack
            data_array = decode_h02(data)
        elif port == 6027:  # Teltonika
            return
        else:
            return

        if len(data_array) > 0:
            for data_dict in data_array:
                print(data_dict)
                # Iniciar el procesamiento de datos en segundo plano
                await self.process_data(port, data_dict)

        # Retornar inmediatamente para indicar que la ejecución ha terminado
        return

    async def handle_client(self, reader, writer):
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
