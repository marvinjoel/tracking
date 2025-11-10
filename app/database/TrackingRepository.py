from datetime import datetime
from psycopg2 import sql


class TrackingRepository:
    """
    Su única responsabilidad es ejecutar consultas.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def save_summary_data(self, summary_data: dict):
        if not self.cursor:
            print("ERROR: No hay cursor de BD. No se puede guardar el resumen.")
            return

        print("Guardando resumen en la base de datos PostgreSQL...")
        run_time = datetime.now()

        for track_id, data in summary_data.items():
            if track_id == "message":
                continue

            insert_query = sql.SQL("""
                                   INSERT INTO tracking_summary (track_id, tiempo_visible_total_str,
                                                                 tiempo_invisible_total_str,
                                                                 last_seen_timestamp, last_disappeared_timestamp,
                                                                 run_timestamp)
                                   VALUES (%s, %s, %s, %s, %s, %s)
                                   """)

            self.cursor.execute(insert_query, (
                track_id,
                data.get("Tiempo Visible Total"),
                data.get("Tiempo Invisible Total"),
                data.get("Visto por última vez"),
                data.get("Desapareció por última vez"),
                run_time
            ))
        print(f"Resumen de {len(summary_data)} tracks guardado en la BD.")

    def log_event(self, track_id: str, event_type: str):
        """
        Tarea Nueva: Guarda el evento de movimiento
        """
        if not self.cursor:
            return

        try:
            insert_query = sql.SQL("""
                                   INSERT INTO tracking_events (track_id, tipo_evento)
                                   VALUES (%s, %s)
                                   """)
            self.cursor.execute(insert_query, (track_id, event_type))

        except Exception as e:
            print(f"Error al registrar evento en BD: {e}")

    def get_events_by_track_id(self, track_id: str):
        """
        Obtiene todos los eventos de movimiento para un ID específico,
        ordenados por tiempo.
        """
        if not self.cursor:
            return []

        try:
            query = sql.SQL("""
                            SELECT timestamp_evento, tipo_evento
                            FROM tracking_events
                            WHERE track_id = %s
                            ORDER BY timestamp_evento ASC
                            """)

            self.cursor.execute(query, (track_id,))
            return self.cursor.fetchall()  # Devuelve una lista de (timestamp, evento)

        except Exception as e:
            print(f"Error al leer eventos de la BD: {e}")
            return []