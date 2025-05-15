import os
from dotenv import load_dotenv
from src.db.database import Database
import mysql.connector
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class DeviceGeofenceController:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST_TRACCAR"),
            "user": os.getenv("DB_USER_TRACCAR"),
            "password": os.getenv("DB_PASSWORD_TRACCAR"),
            "database": os.getenv("DB_NAME_TRACCAR"),
            "port": os.getenv("DB_PORT_TRACCAR", 3306),
        }
        self.db = Database(**self.db_config)

    def get_geofences(self, device_id):
        connection = (
            self.db.get_connection()
        )
        if connection and connection.is_connected():
            try:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT g.name, g.area FROM tc_device_geofence dg JOIN tc_geofences g ON dg.geofenceid = g.id WHERE dg.deviceid = %s"
                cursor.execute(query, (device_id,))
                geofences = (
                    cursor.fetchall()
                )
                cursor.close()
                return geofences
            except mysql.connector.Error as e:
                logger.error(
                    f"Error de BD en get_geofences para device_id {device_id}: {e}"
                )
                self.db.close_connection()
                return None
        logger.warning(
            f"get_geofences: No se pudo obtener conexión para device_id {device_id}"
        )
        return None

    def close(self):
        """Cierra la conexión de la instancia de Database de este controlador."""
        if hasattr(self, "db") and self.db:
            self.db.close_connection()
