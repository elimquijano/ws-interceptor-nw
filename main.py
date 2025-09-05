import asyncio
import logging
from src.tcp.tcp_server import ListenTCPandUCPServer
from src.ws.ws_server import WebSocketServer
from src.utils.logger_config import setup_logging

setup_logging()  # Configurar logging al inicio
logger = logging.getLogger(__name__)


async def main():
    listen_server = ListenTCPandUCPServer()
    ws_server = WebSocketServer()

    # Crear una lista de tareas a ejecutar y limpiar
    server_tasks = []
    try:
        logger.info("Iniciando servidores TCP y WebSocket...")

        # Crear tareas para cada servidor
        listen_task = asyncio.create_task(listen_server.start(), name="TCPServerTask")
        server_tasks.append(listen_task)

        ws_task = asyncio.create_task(ws_server.start(), name="WebSocketServerTask")
        server_tasks.append(ws_task)

        # Esperar a que todas las tareas principales terminen (o una falle)
        # Si una tarea falla con una excepción, asyncio.gather la propagará.
        # Si se cancelan, asyncio.gather también las manejará.
        await asyncio.gather(*server_tasks)

    except asyncio.CancelledError:
        logger.info(
            "Proceso principal (main) cancelado. Iniciando detención de servidores..."
        )
    except Exception as e:
        logger.critical(
            f"Error crítico no manejado en el bucle principal de main: {e}",
            exc_info=True,
        )
    finally:
        logger.info("Iniciando proceso de detención y limpieza de recursos...")

        # Cancelar tareas de servidor si aún están corriendo
        for task in server_tasks:
            if not task.done():
                task.cancel()
                logger.info(f"Tarea {task.get_name()} marcada para cancelación.")

        # Esperar a que las tareas canceladas realmente terminen
        # y capturar CancelledError para evitar que se propaguen más allá.
        if server_tasks:
            await asyncio.gather(*server_tasks, return_exceptions=True)
            logger.info("Tareas de servidor finalizadas o canceladas.")

        # WebSocketServer maneja su AppRunner y su EventNotifier
        if ws_server:
            if ws_server.app_runner:
                await ws_server.app_runner.cleanup()
                logger.info("WebSocketServer AppRunner limpiado.")
            if ws_server.event_notifier:
                await ws_server.event_notifier.close_http_session()
                logger.info("Sesión HTTP del EventNotifier de WebSocketServer cerrada.")

        logger.info("Proceso de detención y limpieza de recursos completado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Aplicación interrumpida por el usuario (Ctrl+C desde consola).")
    finally:
        logger.info("Aplicación finalizada.")
