import psycopg2
import os
from dotenv import load_dotenv


load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

class DatabaseConnection:
    """
     ciclo de vida de la conexión a la base de datos.
    """
    def __init__(self):
        self.conn = None
        self.cursor = None
        try:
            self.conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                port=DB_PORT
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            print(f"Conectado exitosamente a PostgreSQL (Host: {DB_HOST})")

        except psycopg2.OperationalError as e:
            print(f"ERROR: No se pudo conectar a PostgreSQL.")
            print(f"Detalle del error: {e}")
            self.conn = None
            self.cursor = None

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Conexión a PostgreSQL cerrada.")