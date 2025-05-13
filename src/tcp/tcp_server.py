import asyncio
import json
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.sender.position import Position
from src.tcp.sender.events import Events
from datetime import datetime
import logging

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constantes para puertos
PORT_COBAN = 6001
PORT_SINOTRACK = 6013
PORT_TELTONIKA = 6027

# Constantes para tipos de datos
TYPE_CONEXION = "conexion"
TYPE_POSITION = "position"
TYPE_EVENT = "event"
EVENT_TYPE_UNKNOWN = "unknown"

# Tamaño máximo del mensaje esperado para evitar OOM si un cliente envía datos basura muy grandes
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB, ajusta según tus necesidades


class TCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 7005):
        self.host = host
        self.port = port
        self.position_handler = Position()
        self.events_handler = Events()

        # Un mapeo de puertos a decodificadores puede ser más limpio si tienes muchos
        self.decoders = {
            PORT_COBAN: decode_gps103,
            PORT_SINOTRACK: decode_h02,
            # PORT_TELTONIKA: decode_teltonika, # Si tuvieras un decodificador
        }

    async def process_data(self, port: int, data: dict):
        """
        Procesa los datos decodificados y crea tareas para su manejo.
        """
        data_type = data.get("type")  # Usar .get() para evitar KeyError si "type" falta

        if data_type == TYPE_CONEXION:
            # No es necesario crear 'p' aquí si self.position_handler ya existe
            asyncio.create_task(self.position_handler.update_lastupdate(port, data))
        elif data_type == TYPE_POSITION:
            asyncio.create_task(self.position_handler.update_position(port, data))
        elif data_type == TYPE_EVENT and data.get("event_type") != EVENT_TYPE_UNKNOWN:
            logging.info(f"Pasando a enviar evento a usuarios para puerto {port}")
            asyncio.create_task(self.events_handler.send_events_to_users(port, data))
        elif data_type is None:
            logging.warning(f"Dato recibido sin 'type' para puerto {port}: {data}")
        # else:
        # logging.debug(f"Tipo de dato no manejado '{data_type}' o evento desconocido.")

    async def tcp_to_json(self, port: int, message_data: str):
        """
        Decodifica los datos crudos del dispositivo GPS a un formato estructurado (lista de dicts).
        Luego procesa cada diccionario.
        """

        decoder_func = self.decoders.get(port)
        data_array = []

        if decoder_func:
            try:
                data_array = decoder_func(message_data)
            except Exception as e:
                logging.error(
                    f"Error decodificando datos para puerto {port} con {decoder_func.__name__}: {e}"
                )
                logging.debug(f"Datos crudos que causaron error: {message_data}")
                return  # No continuar si la decodificación falla
        else:
            logging.warning(f"No hay decodificador configurado para el puerto {port}.")
            return

        if data_array:  # Asegurarse que data_array no sea None y tenga elementos
            logging.info(f"Puerto {port} decodificó {len(data_array)} mensajes.")
            for data_dict in data_array:
                logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {port} - {data_dict}") # Esto puede ser muy verboso
                await self.process_data(port, data_dict)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Maneja una conexión de cliente individual.
        Lee los datos, los acumula hasta tener un JSON completo, y luego los procesa.
        """
        peername = writer.get_extra_info("peername")
        full_data_buffer = (
            bytearray()
        )

        try:
            while True:
                data_chunk = await reader.read(4096)  # Leer trozos de hasta 4KB

                if not data_chunk:
                    # El cliente cerró la conexión o terminó de enviar datos para este "mensaje"
                    if (
                        not full_data_buffer
                    ):  # Si no se acumuló nada y cierra, no hacer nada.
                        logging.info(
                            f"Conexión cerrada por {peername} sin enviar datos."
                        )
                    break  # Salir del bucle de lectura de trozos

                full_data_buffer.extend(data_chunk)

                # Protección contra mensajes excesivamente grandes
                if len(full_data_buffer) > MAX_MESSAGE_SIZE:
                    logging.error(
                        f"Mensaje de {peername} excede MAX_MESSAGE_SIZE ({MAX_MESSAGE_SIZE} bytes). Descartando y cerrando."
                    )
                    full_data_buffer.clear()  # Liberar memoria
                    # No es necesario 'break' aquí, el finally cerrará. O podríamos cerrar activamente.
                    writer.close()  # Cerrar activamente en este caso
                    await writer.wait_closed()
                    return  # Terminar el handler para esta conexión

            if full_data_buffer:  # Solo procesar si hemos recibido algo
                try:
                    # Decodificar una vez que todos los datos han sido recibidos
                    decoded_string = full_data_buffer.decode("utf-8")
                    received_json = json.loads(decoded_string)

                    port = received_json.get("port")  # Usar .get() para seguridad
                    message_data = received_json.get("data")

                    if port is None or message_data is None:
                        logging.error(
                            f"JSON de {peername} no contiene 'port' o 'data'. Datos: {decoded_string[:500]}..."
                        )
                    else:
                        await self.tcp_to_json(port, message_data)

                except json.JSONDecodeError as e:
                    logging.error(f"Receiver: JSON inválido de {peername}: {e}")
                    # Al loguear datos crudos, tener cuidado con la longitud y la codificación
                    logging.debug(
                        f"Receiver: Datos crudos (UTF-8 intentado, primeros 500B) de {peername}: {full_data_buffer[:500].decode('utf-8', errors='replace')}"
                    )
                except (
                    KeyError
                ) as e:  # Aunque con .get() es menos probable, lo dejamos por si acaso
                    logging.error(
                        f"Receiver: Falta la clave esperada en JSON de {peername}: {e}"
                    )
                except UnicodeDecodeError as e:
                    logging.error(
                        f"Receiver: No se pudo decodificar datos de {peername} como UTF-8: {e}"
                    )
                    logging.debug(
                        f"Receiver: Datos crudos (hex, primeros 256B) de {peername}: {full_data_buffer[:256].hex()}"
                    )
            # else:
            # logging.info(f"No se recibieron datos completos de {peername} antes del cierre de la conexión.")

        except ConnectionResetError:
            logging.warning(f"Conexión reseteada por el peer: {peername}")
        except asyncio.CancelledError:
            logging.info(f"Tarea handle_client para {peername} cancelada.")
            raise  # Re-lanzar para que asyncio maneje la cancelación correctamente
        except Exception as e:
            logging.error(
                f"Excepción inesperada manejando cliente {peername}: {e}", exc_info=True
            )  # exc_info=True para traceback
        finally:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = (
            server.sockets[0].getsockname()
            if server.sockets
            else (self.host, self.port)
        )
        logging.info(f"Servidor TCP escuchando en {addr[0]}:{addr[1]}")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Servidor TCP detenido por el usuario (KeyboardInterrupt).")
        except Exception as e:
            logging.error(
                f"Error crítico en el bucle principal del servidor: {e}", exc_info=True
            )
        finally:
            logging.info("Servidor TCP finalizado.")
