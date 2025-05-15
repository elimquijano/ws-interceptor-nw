import os
from dotenv import load_dotenv
from src.db.database import Database
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class UserDevicesController:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST_TRACCAR"),
            "user": os.getenv("DB_USER_TRACCAR"),
            "password": os.getenv("DB_PASSWORD_TRACCAR"),
            "database": os.getenv("DB_NAME_TRACCAR"),
            "port": os.getenv("DB_PORT_TRACCAR", 3306),
        }
        self.db = Database(**self.db_config)

    def get_users(self, device_id):
        connection = (
            self.db.get_connection()
        )
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT ud.userid FROM tc_user_device ud WHERE ud.deviceid = %s"
                cursor.execute(query, (device_id,))
                users = cursor.fetchall()
                cursor.close()
                return users
            except Error as e:
                logger.error(
                    f"Error de BD en get_users para device_id {device_id}: {e}"
                )
                self.db.close_connection()
                return None
        logger.warning(
            f"get_users: No se pudo obtener conexión para device_id {device_id}"
        )
        return None

    def get_devices(self, user_id):
        connection = (
            self.db.get_connection()
        )
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT ud.deviceid FROM tc_user_device ud WHERE ud.userid = %s"
                cursor.execute(query, (user_id,))
                devices = cursor.fetchall()
                cursor.close()
                return devices
            except Error as e:
                logger.error(f"Error de BD en get_devices para user_id {user_id}: {e}")
                self.db.close_connection()
                return None
        logger.warning(
            f"get_devices: No se pudo obtener conexión para user_id {user_id}"
        )
        return None

    def close(self):
        """Cierra la conexión de la instancia de Database de este controlador."""
        if hasattr(self, "db") and self.db:
            self.db.close_connection()
