import threading
from server.websocket_server import start_websocket_server
from server.tcp_server import start_tcp_server

if __name__ == "__main__":
    # Iniciar el servidor WebSocket en un hilo separado
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.start()

    # Iniciar el servidor TCP en el hilo principal
    start_tcp_server()
