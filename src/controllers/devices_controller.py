import os
from dotenv import load_dotenv
import requests
from src.db.database import Database
from src.utils.common import API_URL_ADMIN_NWPERU
import mysql.connector
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class DevicesController:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST_TRACCAR"),
            "user": os.getenv("DB_USER_TRACCAR"),
            "password": os.getenv("DB_PASSWORD_TRACCAR"),
            "database": os.getenv("DB_NAME_TRACCAR"),
            "port": os.getenv("DB_PORT_TRACCAR", 3306),
        }
        self.db = Database(**self.db_config)

    def get_devices(self):
        """Obtiene todos los dispositivos desde la API externa."""
        try:
            url = f"{API_URL_ADMIN_NWPERU}alldevices-info"
            response = requests.get(url, timeout=10)  # Timeout de 10 segundos
            response.raise_for_status()  # Levanta HTTPError para respuestas 4xx/5xx
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al obtener dispositivos de {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error HTTP al obtener dispositivos de {url}: {e.response.status_code} - {e.response.text[:200]}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al obtener dispositivos de {url}: {e}")
            return None
        except (
            ValueError
        ) as e:  # Error de JSONDecodeError si la respuesta no es JSON válido
            logger.error(f"Error decodificando JSON de {url}: {e}")
            return None

    def get_user(
        self, user_id
    ):
        connection = self.db.get_connection()
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor(dictionary=True)
                query = (
                    "SELECT * FROM users WHERE id = %s"
                )
                cursor.execute(query, (user_id,))
                user = cursor.fetchone()
                cursor.close()
                return user
            except mysql.connector.Error as e:
                logger.error(f"Error de BD en get_user para user_id {user_id}: {e}")
                self.db.close_connection()
                return None
        logger.warning(f"get_user: No se pudo obtener conexión para user_id {user_id}")
        return None

    def close(self):
        """Cierra la conexión de la instancia de Database de este controlador."""
        if hasattr(self, "db") and self.db:
            self.db.close_connection()
