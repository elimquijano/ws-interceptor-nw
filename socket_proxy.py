import socket
import json

# Puerto para recibir los datos en crudo
RAW_DATA_PORT = 7005

# Función para convertir los datos crudos a un formato JSON
def parse_sinotrack_data(raw_data):
    try:
        # Limpiar la cadena y eliminar el carácter de byte (b'...')
        data = raw_data.strip()

        # Asegurarnos que la cadena comience con '*HQ' y terminamos con '#'
        if not data.startswith('*HQ') or not data.endswith('#'):
            return json.dumps({"error": "Datos no válidos o mal formateados"}, indent=4)
        
        # Eliminar los caracteres de control del inicio y final
        data = data[3:-1]

        # Separar los campos por comas
        fields = data.split(',')

        # Verificar que tengamos el número correcto de campos (en este caso 17)
        if len(fields) < 17:
            return json.dumps({"error": "Formato de datos no válido"}, indent=4)

        # Crear un diccionario con los datos procesados
        parsed_data = {
            "device_id": fields[1],  # ID del dispositivo
            "protocol_version": fields[2],  # Versión del protocolo
            "timestamp": fields[3],  # Hora en HHMMSS
            "status": fields[4],     # Estado de la señal del GPS (A o V)
            "latitude": fields[5],   # Latitud
            "latitude_direction": fields[6],  # Dirección de la latitud (N/S)
            "longitude": fields[7],  # Longitud
            "longitude_direction": fields[8],  # Dirección de la longitud (E/O)
            "speed": fields[9],      # Velocidad (en nudos)
            "date": fields[10],      # Fecha en formato DDMMYY
            "device_status": fields[11],  # Estado adicional del dispositivo (probablemente)
            "additional_info": fields[12],  # Información adicional del dispositivo (probablemente)
            "unknown_value1": fields[13],  # Un campo que puede estar relacionado con el estado del dispositivo
            "unknown_value2": fields[14],  # Otro campo de estado o configuración
            "distance_since_last": fields[15],  # Distancia desde el último punto
            "checksum": fields[16],  # El valor de checksum (probablemente de integridad de datos)
        }

        # Convertir los datos a JSON
        return json.dumps(parsed_data, indent=4)

    except Exception as e:
        return json.dumps({"error": f"Ocurrió un error al procesar los datos: {e}"}, indent=4)


# Función para escuchar y procesar los datos en el puerto 7005
def listen_for_data():
    # Crear el socket TCP para recibir datos
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', RAW_DATA_PORT))
    server_socket.listen(5)
    
    print(f"Escuchando en el puerto {RAW_DATA_PORT}...")

    while True:
        # Aceptar una conexión entrante
        client_socket, client_address = server_socket.accept()
        print(f"Conexión aceptada desde {client_address}")

        try:
            # Recibir los datos
            while True:
                data = client_socket.recv(1024)  # Recibe hasta 1024 bytes
                if not data:
                    break
                try:
                    received_json = json.loads(data.decode("utf-8"))
                    port = received_json["port"]
                    message_data = received_json["data"]
                    
                    if port == 6013:
                        # Procesar los datos y convertir a JSON
                        json_data = parse_sinotrack_data(message_data)

                        # Imprimir el JSON
                        print(json_data)
                    else:
                        print(f"{port}: {message_data}")
                except json.JSONDecodeError as e:
                    print(f"Error al decodificar JSON: {e}")

        except Exception as e:
            print(f"Error al recibir datos: {e}")
        finally:
            client_socket.close()
            print(f"Conexión cerrada con {client_address}")

# Iniciar el servidor para escuchar en el puerto 7005
if __name__ == "__main__":
    listen_for_data()


""" import threading
from server.websocket_server import start_websocket_server
from server.tcp_server import start_tcp_server

if __name__ == "__main__":
    # Iniciar el servidor WebSocket en un hilo separado
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.start()

    # Iniciar el servidor TCP en el hilo principal
    start_tcp_server()
 """