import asyncio
import websockets
from .utils import authenticate_client, clients


async def handle_client(websocket, path):
    print("handle_client is being executed!")
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
    async with websockets.serve(handle_client, "0.0.0.0", 7006):
        print("WebSocket server listening on port 7006")
        await asyncio.Future()  # run forever


def start_websocket_server():
    try:
        asyncio.get_running_loop().create_task(main())
    except RuntimeError:
        asyncio.run(main())
