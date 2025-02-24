import asyncio
import websockets
from urllib.parse import urlparse
from .utils import authenticate_client, clients

async def handle_client(websocket):
    print("handle_client is being executed!")
    # Get the path and query string from the websocket connection
    path = websocket.path
    
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

async def main():
    server = await websockets.serve(handle_client, "0.0.0.0", 7006)
    print("WebSocket server listening on port 7006")
    await server.wait_closed()

def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())