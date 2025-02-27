import os
from dotenv import load_dotenv
from src.db.database import Database

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


class DevicesController:
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

    def get_devices(self):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT d.*, p.latitude, p.longitude, p.speed, p.course FROM tc_devices d LEFT JOIN tc_positions p ON d.positionid = p.id"
            cursor.execute(query)
            devices = cursor.fetchall()
            cursor.close()
            return devices
        return None

    def get_user(self, user_id):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            cursor.close()
            return user
        return None

    def create_user(self, username, email):
        connection = self.db.get_connection()
        if connection:
            cursor = connection.cursor()
            query = "INSERT INTO users (username, email) VALUES (%s, %s)"
            cursor.execute(query, (username, email))
            connection.commit()
            cursor.close()
            return cursor.lastrowid
        return None

    def close(self):
        self.db.close_connection()
