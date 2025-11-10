# Este es el archivo database.py

import psycopg2
from psycopg2 import sql
import os
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()


class TrackingRepository:
    """
    APLICA EL PATRÓN REPOSITORIO Y SRP.
    Esta clase es la única en toda la aplicación que sabe
    cómo conectarse y hablar con la base de datos PostgreSQL.
    """

    def __init__(self):
        """
        Inicializa la conexión a la base de datos.
        Para buenas prácticas, lee los detalles de conexión
        de variables de entorno.
        """
        # --- ¡CONFIGURA ESTO! ---
        # Es mejor usar variables de entorno (os.environ.get)
        # pero para el MVP, puedes escribirlos aquí:
        DB_NAME = os.getenv("DB_NAME")
        DB_USER = os.getenv("DB_USER")
        DB_PASS = os.getenv("DB_PASS")
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")

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
            self._create_table_if_not_exists()

        except psycopg2.OperationalError as e:
            print(f"ERROR: No se pudo conectar a PostgreSQL.")
            print("Por favor, asegúrate de que el servidor esté corriendo y")
            print("de que las variables de entorno (DB_NAME, DB_USER, etc.) sean correctas.")
            print(f"\nDetalle del error: {e}")
            self.conn = None
            self.cursor = None

    def _create_table_if_not_exists(self):
        """
        Un método privado que crea la tabla 'tracking_summary'
        si esta no existe ya.
        """
        if not self.cursor:
            return

        create_table_query = """
                             CREATE TABLE IF NOT EXISTS tracking_summary \
                             ( \
                                 id \
                                 SERIAL \
                                 PRIMARY \
                                 KEY, \
                                 track_id \
                                 VARCHAR \
                             ( \
                                 50 \
                             ) NOT NULL,
                                 tiempo_visible_total_str VARCHAR \
                             ( \
                                 50 \
                             ),
                                 tiempo_invisible_total_str VARCHAR \
                             ( \
                                 50 \
                             ),
                                 last_seen_timestamp TIMESTAMPTZ,
                                 last_disappeared_timestamp TIMESTAMPTZ,
                                 run_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                                 ); \
                             """
        self.cursor.execute(create_table_query)
        print("Tabla 'tracking_summary' verificada/creada.")

    def save_summary_data(self, summary_data: dict):
        """
        Toma el diccionario de resumen y lo guarda en la base de datos.
        Usa "INSERT" para guardar un registro por cada ID.
        """
        if not self.cursor:
            print("ERROR: No hay conexión a BD. No se puede guardar el resumen.")
            return

        print("Guardando resumen en la base de datos PostgreSQL...")

        # Obtenemos un timestamp para todo este "lote" de datos
        run_time = datetime.now()

        for track_id, data in summary_data.items():
            if track_id == "message":  # Ignorar el mensaje de "no sujetos"
                continue

            insert_query = sql.SQL("""
                                   INSERT INTO tracking_summary (track_id,
                                                                 tiempo_visible_total_str,
                                                                 tiempo_invisible_total_str,
                                                                 last_seen_timestamp,
                                                                 last_disappeared_timestamp,
                                                                 run_timestamp)
                                   VALUES (%s, %s, %s, %s, %s, %s)
                                   """)

            # Los timestamps pueden ser None, psycopg2 los manejará bien
            self.cursor.execute(insert_query, (
                track_id,
                data.get("Tiempo Visible Total"),
                data.get("Tiempo Invisible Total"),
                data.get("Visto por última vez"),
                data.get("Desapareció por última vez"),
                run_time
            ))

        print(f"Resumen de {len(summary_data)} tracks guardado en la BD.")

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Conexión a PostgreSQL cerrada.")