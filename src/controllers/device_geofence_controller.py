import os
from dotenv import load_dotenv
from src.db.database import Database

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


class DeviceGeofenceController:
    def __init__(self):
        # Configuración de la base de datos específica para este controlador
        self.db_config = {
            "host": os.getenv("DB_HOST_TRACCAR"),
            "user": os.getenv("DB_USER_TRACCAR"),
            "password": os.getenv("DB_PASSWORD_TRACCAR"),
            "database": os.getenv("DB_NAME_TRACCAR"),
        }
        self.db = Database(**self.db_config)
        self.db.create_connection()

    def get_geofences(self, device_id):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT g.name, g.area FROM tc_device_geofence dg JOIN tc_geofences g ON dg.geofenceid = g.id WHERE dg.deviceid = %s"
            cursor.execute(query, (device_id,))
            users = cursor.fetchall()
            cursor.close()
            return users
        return None

    def close(self):
        self.db.close_connection()
