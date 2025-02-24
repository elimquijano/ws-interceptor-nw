import asyncio
import websockets
from urllib.parse import urlparse
from .utils import authenticate_client, clients


async def handle_client(websocket, path):  # Added path parameter
    print(f"Nueva conexión en {path}")

    devices = await authenticate_client(websocket, path)
    if not devices:
        return

    client_id = id(websocket)
    clients[client_id] = {"websocket": websocket, "devices": devices}
    print(f"Client {client_id} connected with devices: {devices}")

    try:
        async for message in websocket:
            print(f"Received message from {client_id}: {message}")
    except websockets.ConnectionClosed:
        print(f"Client {client_id} disconnected")
    finally:
        del clients[client_id]

def start_websocket_server():
    # Crear un nuevo event loop para este hilo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Definir el servidor
    async def start_server():
        server = await websockets.serve(handle_client, "0.0.0.0", 7006)
        print("WebSocket server listening on ws://0.0.0.0:7006")
        await asyncio.Future()  # mantener el servidor corriendo
    
    try:
        # Ejecutar el servidor en el loop
        loop.run_until_complete(start_server())
    except Exception as e:
        print(f"WebSocket server error: {e}")
    finally:
        loop.close()
