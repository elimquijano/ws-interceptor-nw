import asyncio
from src.tcp.tcp_server import TCPServer
from src.ws.ws_server import WebSocketServer

async def main():
    tcp_server = TCPServer()
    ws_server = WebSocketServer()

    try:
        await asyncio.gather(
            tcp_server.start(),
            ws_server.start()
        )
    except Exception as e:
        print(f"Error running servers: {e}")

if __name__ == "__main__":
    asyncio.run(main())