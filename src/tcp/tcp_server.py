import asyncio
import logging
from typing import Tuple
import binascii
from src.tcp.parser.h02 import decode_h02
from src.tcp.parser.gps103 import decode_gps103
from src.tcp.parser.teltonika import decode_teltonika
from src.tcp.parser.osmand import decode_osmand
from src.tcp.sender.position import PositionUpdater
from src.tcp.sender.events import EventNotifierService
from src.ws.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

TYPE_CONNECTION = "conexion"
TYPE_POSITION = "position"
TYPE_EVENT = "event"
EVENT_TYPE_UNKNOWN = "unknown"

MAX_MESSAGE_BIT_SIZE = 4096  # 4 KB
MAX_MESSAGE_TEXT_SIZE = 2048  # 2 KB


class UTF8Server:
    def __init__(self, port=9013):
        self.port = port
        self.running = False
        self.tcp_server = None
        self.udp_transport = None
        self.udp_protocol = None
        self._data_handler = None

    async def start(self):
        """Inicia el servidor TCP y UDP de forma asíncrona"""
        self.running = True

        print(f"Servidor UTF-8 iniciando en puerto {self.port}")

        # Crear tareas para TCP y UDP
        tcp_task = asyncio.create_task(self._start_tcp_server())
        udp_task = asyncio.create_task(self._start_udp_server())

        print(f"Escuchando TCP y UDP...")

        # Esperar a que ambos servidores estén ejecutándose
        try:
            await asyncio.gather(tcp_task, udp_task)
        except asyncio.CancelledError:
            print(f"Servidor cancelado")
        except Exception as e:
            print(f"Error en servidor: {e}")

    async def _start_tcp_server(self):
        """Inicia el servidor TCP"""
        try:
            self.tcp_server = await asyncio.start_server(
                self._handle_tcp_client, "0.0.0.0", self.port
            )

            async with self.tcp_server:
                await self.tcp_server.serve_forever()

        except Exception as e:
            print(f"Error en servidor TCP: {e}")

    async def _handle_tcp_client(self, reader, writer):
        """Maneja conexiones TCP de clientes"""
        client_address = writer.get_extra_info("peername")
        print(f"TCP - Nueva conexión desde {client_address}")

        try:
            while self.running:
                # Leer datos del cliente
                data = await reader.read(MAX_MESSAGE_TEXT_SIZE)
                if not data:
                    break

                # Decodificar en UTF-8 e imprimir
                try:
                    message = data.decode("utf-8")
                    if hasattr(self, "_data_handler") and self._data_handler:
                        self._data_handler(message, client_address, "tcp")
                    print(f"TCP de {client_address}: {repr(message)}")
                except UnicodeDecodeError:
                    print(f"TCP de {client_address}: {data.hex()} (no UTF-8)")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error TCP cliente {client_address}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"TCP - Conexión cerrada desde {client_address}")

    async def _start_udp_server(self):
        """Inicia el servidor UDP"""
        try:
            loop = asyncio.get_running_loop()

            # Crear protocolo UDP
            self.udp_transport, self.udp_protocol = await loop.create_datagram_endpoint(
                lambda: UTF8UDPServer(self), local_addr=("0.0.0.0", self.port)
            )

            # Mantener el servidor UDP ejecutándose
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error en servidor UDP: {e}")
        finally:
            if self.udp_transport:
                self.udp_transport.close()

    async def stop(self):
        """Detiene el servidor"""
        print(f"Deteniendo servidor...")
        self.running = False

        # Cerrar servidor TCP
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()

        # Cerrar transporte UDP
        if self.udp_transport:
            self.udp_transport.close()

        print(f"Servidor detenido")


class UTF8UDPServer(asyncio.DatagramProtocol):
    """Protocolo para manejar datos UDP"""

    def __init__(self, server):
        self.server = server

    def datagram_received(self, data, addr):
        """Maneja datos UDP recibidos"""
        try:
            message = data.decode("utf-8")
            if hasattr(self.server, "_data_handler") and self.server._data_handler:
                self.server._data_handler(message, addr, "udp")
            print(f"UDP de {addr}: {repr(message)}")
        except UnicodeDecodeError:
            print(f"UDP de {addr}: {data.hex()} (no UTF-8)")


class BinaryServer:
    def __init__(self, port: int = 9027):
        self.port = port
        self.running = False
        self.tcp_server = None
        self.udp_transport = None
        self.udp_protocol = None
        self._data_handler = None

    async def handle_tcp_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle TCP client connection asynchronously"""
        address = writer.get_extra_info("peername")
        print(f"TCP client connected from {address}")

        try:
            while self.running:
                # Receive data
                data = await reader.read(MAX_MESSAGE_BIT_SIZE)
                if not data:
                    break
                if hasattr(self, "_data_handler") and self._data_handler:
                    self._data_handler(data, address, "tcp")
                print(f"TCP received {len(data)} bytes from {address}")
                print(f"Raw data: {binascii.hexlify(data).decode()}")

        except asyncio.CancelledError:
            print(f"TCP client {address} connection cancelled")
        except Exception as e:
            print(f"Error handling TCP client {address}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"TCP client {address} disconnected")

    async def _start_tcp_server(self):
        """Start TCP server"""
        try:
            self.tcp_server = await asyncio.start_server(
                self.handle_tcp_client, "0.0.0.0", self.port
            )

            print(f"TCP server started on port {self.port}")

            async with self.tcp_server:
                await self.tcp_server.serve_forever()

        except asyncio.CancelledError:
            print("TCP server cancelled")
        except Exception as e:
            print(f"Error in TCP server: {e}")

    async def _start_udp_server(self):
        """Start UDP server"""
        try:
            loop = asyncio.get_running_loop()

            # Create UDP server
            self.udp_transport, self.udp_protocol = await loop.create_datagram_endpoint(
                lambda: BinaryUDPServer(self), local_addr=("0.0.0.0", self.port)
            )

            print(f"UDP server started on port {self.port}")

            # Keep UDP server running
            while self.running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            print("UDP server cancelled")
        except Exception as e:
            print(f"Error in UDP server: {e}")
        finally:
            if self.udp_transport:
                self.udp_transport.close()

    def handle_udp_data(self, data: bytes, address: Tuple[str, int]):
        """Handle UDP data (called by UDP protocol)"""
        try:
            if hasattr(self, "_data_handler") and self._data_handler:
                self._data_handler(data, address, "udp")
            print(f"UDP received {len(data)} bytes from {address}")
            print(f"Raw data: {binascii.hexlify(data).decode()}")

        except Exception as e:
            print(f"Error handling UDP data: {e}")

    async def start(self):
        """Start the server asynchronously"""
        self.running = True

        print(f"Teltonika server starting on port {self.port}")
        print("Listening for TCP and UDP connections...")

        # Create tasks for TCP and UDP servers
        tcp_task = asyncio.create_task(self._start_tcp_server())
        udp_task = asyncio.create_task(self._start_udp_server())

        try:
            # Wait for both servers to run
            await asyncio.gather(tcp_task, udp_task)
        except asyncio.CancelledError:
            print("Server cancelled")
        except KeyboardInterrupt:
            print("Server shutdown requested")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the server"""
        print("Stopping Teltonika server...")
        self.running = False

        # Close TCP server
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()

        # Close UDP transport
        if self.udp_transport:
            self.udp_transport.close()

        print("Teltonika server stopped")


class BinaryUDPServer(asyncio.DatagramProtocol):
    """UDP Protocol handler for Teltonika server"""

    def __init__(self, server: BinaryServer):
        self.server = server

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle received UDP datagram"""
        self.server.handle_udp_data(data, addr)


class ListenTCPandUCPServer:
    def __init__(self, host: str = "0.0.0.0"):
        self.host = host
        self.ws_manager = WebSocketManager()
        self.event_notifier = EventNotifierService(self.ws_manager)
        self.position_updater = PositionUpdater(self.ws_manager, self.event_notifier)
        self.protocol_ports = {
            5001: {
                "name": "GPS103Protocol",
                "device": "Coban",
                "decoder": decode_gps103,
                "type_data": "utf8",
            },
            6013: {
                "name": "H02Protocol",
                "device": "Sinotrack",
                "decoder": decode_h02,
                "type_data": "utf8",
            },
            6027: {
                "name": "TeltonikaProtocol",
                "device": "Teltonika",
                "decoder": decode_teltonika,
                "type_data": "binary",
            },
            6055: {
                "name": "OsmandProtocol",
                "device": "Traccar Client",
                "decoder": decode_osmand,
                "type_data": "utf8",
            },
        }
        self.running_tasks = []
        self.server_instances = {}
        logger.info(
            f"Servidor de escucha TCP y UDP inicializado para puertos: {list(self.protocol_ports.keys())}"
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

    async def _decode_and_process_data(
        self, device_original_port: int, data: bytes | str, connection_type: str = "tcp"
    ):
        protocol_port = self.protocol_ports.get(device_original_port)
        if not protocol_port:
            logger.warning(
                f"No hay decodificador para puerto original {device_original_port}."
            )
            return

        try:
            # Pasar data tal como llega al decoder junto con el tipo de conexión
            decoded_data_list = protocol_port["decoder"](data, connection_type)
            for data_dict in decoded_data_list:
                if isinstance(data_dict, dict):
                    await self._process_decoded_data(device_original_port, data_dict)
                else:
                    logger.warning(
                        f"Decodificador para {device_original_port} no devolvió dict: {data_dict}"
                    )
        except Exception as e:
            logger.error(
                f"Error decodificando datos para puerto {device_original_port} con {protocol_port['decoder'].__name__}: {e}",
                exc_info=True,
            )
            logger.info(f"Datos crudos que causaron error: {str(data)[:500]}")

    async def start(self):
        try:
            self.running_tasks = []
            self.server_instances = {}

            for port, protocol_info in self.protocol_ports.items():
                if protocol_info["type_data"] == "utf8":
                    server_instance = UTF8Server(port)
                    # Inyectar el handler
                    server_instance._data_handler = self._create_handler(port)
                elif protocol_info["type_data"] == "binary":
                    server_instance = BinaryServer(port)
                    # Inyectar el handler
                    server_instance._data_handler = self._create_handler(port)

                self.server_instances[port] = server_instance
                task = asyncio.create_task(server_instance.start())
                self.running_tasks.append(task)

            logger.info(
                f"Iniciados servidores en puertos: {list(self.protocol_ports.keys())}"
            )

            # Esperar a que todos los servidores estén corriendo
            await asyncio.gather(*self.running_tasks)

        except Exception as e:
            logger.error(f"Error iniciando servidores: {e}")
            await self.stop()

    def _create_handler(self, port):
        """Crear handler para evitar problemas con closures"""

        def handler(data, addr, connection_type):
            return asyncio.create_task(
                self._decode_and_process_data(port, data, connection_type)
            )

        return handler

    async def stop(self):
        try:
            logger.info("Deteniendo servidores...")

            # Detener todas las instancias de servidor
            for server_instance in self.server_instances.values():
                await server_instance.stop()

            # Cancelar todas las tareas
            for task in self.running_tasks:
                if not task.done():
                    task.cancel()

            # Esperar a que las tareas se cancelen
            if self.running_tasks:
                await asyncio.gather(*self.running_tasks, return_exceptions=True)

            logger.info("Todos los servidores detenidos")

        except Exception as e:
            logger.error(f"Error deteniendo servidores: {e}")
        finally:
            self.running_tasks = []
            self.server_instances = {}
