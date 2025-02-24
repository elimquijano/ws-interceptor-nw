import asyncio
import json
from datetime import datetime
from src.ws.ws_manager import WebSocketManager
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.parser.h02 import decode_h02

class TCPServer:
    def __init__(self, host='0.0.0.0', port=7005):
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()
        
    async def tcp_to_json(port, data):
        if port == 6001:
            data_dict = decode_gps103(data)
            print(f"Decoded GPS103 data: {data_dict}")
            return json.dumps(data_dict)
        elif port == 6013:
            data_dict = decode_h02(data)
            print(f"Decoded H02 data: {data_dict}")
            return json.dumps(data_dict)
        else:
            return None

    async def process_message(self, message_json):
        try:
            # Extract port and data from JSON
            port = message_json.get('port')
            data = message_json.get('data')
            
            if not port or not data:
                print("Invalid message format")
                return
            
            # Process based on port (your existing logic)
            processed_data = self.tcp_to_json(port, data)
            
            if not processed_data:
                return
            # Broadcast to WebSocket clients
            #await self.ws_manager.broadcast(processed_data)
            
        except Exception as e:
            print(f"Error processing message: {e}")

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"New TCP connection from {addr}")
        
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                
                try:
                    message_json = json.loads(data.decode())
                    print(f"Received JSON from {addr}: {message_json}")
                    await self.process_message(message_json)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received: {e}")
                
        except Exception as e:
            print(f"Error handling TCP client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        print(f"TCP Server listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()