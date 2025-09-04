# src/tcp/tcp_server.py
import asyncio
import json
import logging
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.parser.osmand import decode_osmand
from src.tcp.sender.position import PositionUpdater
from src.tcp.sender.events import EventNotifierService
from src.ws.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

PORT_COBAN = 6001
PORT_SINOTRACK = 6013
# PORT_TELTONIKA = 6027
PORT_TRACCAR_CLIENT = 6055

TYPE_CONNECTION = "conexion"
TYPE_POSITION = "position"
TYPE_EVENT = "event"
EVENT_TYPE_UNKNOWN = "unknown"

MAX_MESSAGE_SIZE = 10 * 1024 * 1024


class TCPServer:
    def __init__(
        self, host: str = "0.0.0.0", port: int = 7005
    ):  # Puerto del broker JSON
        self.host = host
        self.port = port
        self.ws_manager = WebSocketManager()  # Accede al singleton
        self.event_notifier = EventNotifierService(self.ws_manager)
        self.position_updater = PositionUpdater(self.ws_manager, self.event_notifier)

        self.protocol_decoders = {
            PORT_COBAN: decode_gps103,  # Usa los nombres de función de tus parsers
            PORT_SINOTRACK: decode_h02,
            PORT_TRACCAR_CLIENT: decode_osmand,
        }
        logger.info(
            f"TCPServer inicializado para JSON broker en {self.host}:{self.port}."
        )

    async def _process_decoded_data(
        self, device_original_port: int, data_payload: dict
    ):
        data_type = data_payload.get("type")
        if data_type == TYPE_CONNECTION:
            await self.position_updater.update_device_last_seen(data_payload)
        elif data_type == TYPE_POSITION:
            await self.position_updater.process_position_update(data_payload)
        elif (
            data_type == TYPE_EVENT
            and data_payload.get("event_type") != EVENT_TYPE_UNKNOWN
        ):
            await self.event_notifier.process_event_from_device(data_payload)
        elif data_type is None:
            logger.warning(
                f"Dato sin 'type' de puerto {device_original_port}: {data_payload}"
            )

    async def _decode_and_process_raw_gps_data(
        self, device_original_port: int, raw_message_data: str
    ):
        decoder_function = self.protocol_decoders.get(device_original_port)
        if not decoder_function:
            logger.warning(
                f"No hay decodificador para puerto original {device_original_port}."
            )
            return
        try:
            # Tus parsers devuelven una lista de dicts
            decoded_data_list = decoder_function(raw_message_data)
            for data_dict in decoded_data_list:
                if isinstance(data_dict, dict):
                    logger.info(
                        f"{device_original_port} - {data_dict}"
                    )  # Log de datos decodificados
                    await self._process_decoded_data(device_original_port, data_dict)
                else:
                    logger.warning(
                        f"Decodificador para {device_original_port} no devolvió dict: {data_dict}"
                    )
        except Exception as e:
            logger.error(
                f"Error decodificando datos para puerto {device_original_port} con {decoder_function.__name__}: {e}",
                exc_info=True,
            )
            logger.debug(
                f"Datos crudos (GPS) que causaron error: {raw_message_data[:500]}"
            )

    async def handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        peername = writer.get_extra_info("peername")
        logger.debug(f"Nueva conexión TCP (JSON broker) de: {peername}")
        full_data_buffer = bytearray()
        try:
            while True:
                data_chunk = await reader.read(4096)
                if not data_chunk:
                    if not full_data_buffer:
                        logger.debug(f"Conexión de {peername} cerrada sin datos.")
                    break
                full_data_buffer.extend(data_chunk)
                if len(full_data_buffer) > MAX_MESSAGE_SIZE:
                    logger.error(
                        f"Mensaje de {peername} excede MAX_MESSAGE_SIZE. Descartando y cerrando."
                    )
                    full_data_buffer.clear()
                    writer.close()
                    await writer.wait_closed()
                    return

            if full_data_buffer:
                try:
                    decoded_json_str = full_data_buffer.decode(
                        "utf-8", errors="replace"
                    )
                    json_wrapper = json.loads(decoded_json_str)
                    device_port = json_wrapper.get("port")
                    raw_gps_data = json_wrapper.get("data")
                    if device_port == 6027:
                        logger.info(
                            f"Datos recibidos de Teltonika (puerto 6027): {raw_gps_data}"
                        )
                    if device_port is not None and raw_gps_data is not None:
                        await self._decode_and_process_raw_gps_data(
                            device_port, raw_gps_data
                        )
                    else:
                        logger.error(
                            f"JSON de {peername} sin 'port' o 'data'. Datos: {decoded_json_str[:200]}..."
                        )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"JSON inválido (wrapper) de {peername}: {e}. Datos: {full_data_buffer.decode('utf-8', errors='replace')[:500]}"
                    )
                except UnicodeDecodeError as e:
                    logger.error(
                        f"Error de decodificación Unicode (wrapper) de {peername}: {e}. Datos (hex): {full_data_buffer[:256].hex()}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error procesando JSON wrapper de {peername}: {e}",
                        exc_info=True,
                    )
        except ConnectionResetError:
            logger.warning(f"Conexión reseteada por {peername}")
        except asyncio.CancelledError:
            logger.info(f"Tarea handle_client para {peername} cancelada.")
            raise
        except Exception as e:
            logger.error(
                f"Excepción inesperada manejando {peername}: {e}", exc_info=True
            )
        finally:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            logger.debug(f"Conexión con {peername} finalizada.")

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client_connection, self.host, self.port
        )
        addr = (
            server.sockets[0].getsockname()
            if server.sockets
            else (self.host, self.port)
        )
        logger.info(f"Servidor TCP (JSON broker) escuchando en {addr[0]}:{addr[1]}")
        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logger.info("Servidor TCP (JSON broker) cancelado.")
        except Exception as e:
            logger.critical(
                f"Error crítico en bucle principal del servidor TCP: {e}", exc_info=True
            )
        finally:
            logger.info("Servidor TCP (JSON broker) finalizando...")
            if self.event_notifier:
                await self.event_notifier.close_http_session()
            if self.position_updater:
                await self.position_updater._close_internal_controllers()
            logger.info(
                "Servidor TCP (JSON broker) finalizado y recursos internos limpiados."
            )
