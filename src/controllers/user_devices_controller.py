import os
from dotenv import load_dotenv
from src.db.database import Database

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

class UserDevicesController:
    def __init__(self):
        # Configuración de la base de datos específica para este controlador
        self.db_config = {
            "host": os.getenv("DB_HOST_TRACCAR"),
            "user": os.getenv("DB_USER_TRACCAR"),
            "password":  os.getenv("DB_PASSWORD_TRACCAR"),
            "database": os.getenv("DB_NAME_TRACCAR"),
        }
        self.db = Database(**self.db_config)
        self.db.create_connection()

    def get_users(self, device_id):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT ud.userid FROM tc_user_device ud WHERE ud.deviceid = %s"
            cursor.execute(query, (device_id,))
            users = cursor.fetchall()
            cursor.close()
            return users
        return None

    def get_devices(self, user_id):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT ud.deviceid FROM tc_user_device ud WHERE ud.userid = %s"
            cursor.execute(query, (user_id,))
            devices = cursor.fetchall()
            cursor.close()
            return devices
        return None

    def close(self):
        self.db.close_connection()
