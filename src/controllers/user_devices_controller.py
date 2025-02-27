from src.db.database import Database

class UserDevicesController:
    def __init__(self):
        # Configuración de la base de datos específica para este controlador
        self.db_config = {
            'host': '159.65.107.11',
            'user': 'usernatcrt',
            'password': '454RURNEW-347r3432ols',
            'database': 'traccar_v2'
        }
        self.db = Database(**self.db_config)
        self.db.create_connection()

    def get_user(self, device_id):
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
