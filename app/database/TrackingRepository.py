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

    def log_event(self, camera_id: str, track_id: str, event_type: str):
        """
        Tarea Nueva: Guarda el evento de movimiento
        """
        if not self.cursor:
            return

        try:
            insert_query = sql.SQL("""
                                   INSERT INTO tracking_events (camera_id, track_id, tipo_evento) 
                                    VALUES (%s, %s, %s)
                                   """)
            self.cursor.execute(insert_query, (camera_id, track_id, event_type))

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

    def is_schedule_active(self) -> bool:
        """
        Verifica si hay un horario activo en la BD para
        el día y la hora actuales.
        """
        if not self.cursor:
            return False  # Si no hay BD, no podemos chequear

        try:
            # 1. Obtenemos el día y la hora actuales
            now = datetime.now()
            current_day_of_week = now.weekday()  # 0=Lunes, 1=Martes, etc.
            current_time = now.time()  # Ej. 10:30:00

            # 2. Creamos la consulta
            query = sql.SQL("""
                            SELECT COUNT(*)
                            FROM horarios_medicion
                            WHERE dia_semana = %s
                              AND hora_inicio <= %s
                              AND hora_fin >= %s
                            """)

            # 3. Ejecutamos
            self.cursor.execute(query, (
                current_day_of_week,
                current_time,
                current_time
            ))

            # 4. Obtenemos el resultado (el valor de COUNT(*))
            count = self.cursor.fetchone()[0]

            return count > 0  # Si es > 0, ¡hay un horario activo!

        except Exception as e:
            print(f"Error al chequear horario en BD: {e}")
            return False

    def get_active_cameras(self) -> list:
        """
        Obtiene una lista de todas las cámaras marcadas como 'esta_activa = true'.
        """
        if not self.cursor:
            return []

        try:
            query = sql.SQL("""
                            SELECT id, url_rtsp, algoritmo_a_usar
                            FROM lista_camaras
                            WHERE esta_activa = true
                            """)

            self.cursor.execute(query)
            return self.cursor.fetchall()

        except Exception as e:
            print(f"Error al leer la lista de cámaras activas: {e}")
            return []