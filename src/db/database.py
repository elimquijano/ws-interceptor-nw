import mysql.connector
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, host, user, password, database, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None
        self.connection_id_log = None

    def create_connection(self):
        if self.connection and self.connection.is_connected():
            # logger.debug(f"Usando conexión existente a {self.database} (ID: {self.connection_id_log})")
            return self.connection
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=True,
            )
            if self.connection.is_connected():
                self.connection_id_log = self.connection.connection_id
                # logger.info(f"Nueva conexión exitosa a BD: {self.database}@{self.host} (Conn ID: {self.connection_id_log})")
                pass
            else:
                self.connection = None
        except Error as e:
            logger.error(f"Error al conectar a BD {self.database}@{self.host}: {e}")
            self.connection = None
        return self.connection

    def close_connection(self):
        if self.connection and self.connection.is_connected():
            conn_id_before_close = self.connection_id_log
            try:
                self.connection.close()
                # logger.info(f"Conexión a BD {self.database}@{self.host} (Conn ID: {conn_id_before_close}) cerrada.")
            except Error as e:
                logger.error(
                    f"Error al cerrar conexión a BD (Conn ID: {conn_id_before_close}): {e}"
                )
            finally:
                self.connection = None
                self.connection_id_log = None

    def get_connection(self):
        # Si la conexión se perdió o no se estableció, intentar crearla/recrearla.
        if self.connection is None or not self.connection.is_connected():
            # logger.warning(f"Conexión a BD no disponible o cerrada. Intentando (re)conectar a {self.database}@{self.host}...")
            self.create_connection()
        return self.connection
