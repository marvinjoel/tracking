from datetime import datetime, timedelta

class TrackedSubject:

    def __init__(self, track_id: int) -> None:
        self.track_id: int = track_id
        self.is_visible: bool = True
        self.last_seen: datetime = datetime.now()
        self.last_disappeared = None
        self.total_visible_time: timedelta = timedelta(0)
        self.total_invisible_time: timedelta = timedelta(0)
        print(f"NUEVO SUJETO: ID {self.track_id} detectado.")

    def mark_visible(self) -> None:
        """
        Marca al sujeto como visible en el frame actual.
        Calcula el tiempo invisible si estaba desaparecido.
        """
        current_time = datetime.now()
        if not self.is_visible:
            # --- ACABA DE REAPARECER ---
            # 1. Calculamos el tiempo que estuvo fuera
            if self.last_disappeared:
                invisible_duration = current_time - self.last_disappeared
                self.total_invisible_time += invisible_duration
                print(f"REGRESA: ID {self.track_id} | Tiempo fuera: {invisible_duration}")

            # 2. Guardamos la hora de inicio de esta NUEVA sesión visible
            #    ¡¡ESTA ES LA CORRECCIÓN!!
            #    Solo actualizamos 'last_seen' cuando no estaba visible.
            self.last_seen = current_time

        # 3. Marcamos que está visible
        self.is_visible = True

    def mark_invisible(self) -> None:
        """
        Marca al sujeto como invisible.
        Calcula el tiempo visible de su última sesión.
        """
        current_time: datetime = datetime.now()
        if self.is_visible:
            # Acaba de desaparecer
            visible_duration: timedelta = current_time - self.last_seen
            self.total_visible_time += visible_duration
            print(f"DESAPARECE: ID {self.track_id} | Tiempo visto: {visible_duration}")

        self.is_visible = False
        self.last_disappeared = current_time

    def get_visible_time_str(self) -> str:
        """
        Devuelve el tiempo visible total (para mostrar en pantalla).
        Incluye la sesión actual si está visible.
        """
        current_session_time: timedelta = timedelta(0)
        if self.is_visible:
            # Sumar el tiempo de la sesión actual que aún no se ha "guardado"
            current_session_time: timedelta = datetime.now() - self.last_seen

        total_seconds = (self.total_visible_time + current_session_time).total_seconds()
        return f"{total_seconds:.1f}s"


class StateManager:
    """
    Esta clase gestiona la COLECCIÓN de sujetos.
    Actúa como un Patrón de Diseño "Manager" o "Repository" simple.
    No sabe de YOLO ni de SORT, solo recibe una lista de IDs.
    """

    def __init__(self) -> None:
        self.subjects = {}

    def update_states(self, visible_track_ids) -> None:
        """
        El "corazón" del programa. Sincroniza nuestro estado
        con lo que SORT acaba de ver en el frame actual.
        """
        visible_set = set(visible_track_ids)
        tracked_set = set(self.subjects.keys())

        # --- 1. Manejar sujetos que desaparecieron ---
        # (Están en nuestra lista pero no en la lista de SORT)
        disappeared_ids = tracked_set - visible_set
        for track_id in disappeared_ids:
            if self.subjects[track_id].is_visible:
                self.subjects[track_id].mark_invisible()

        # --- 2. Manejar sujetos nuevos o que siguen visibles ---
        # (Están en la lista de SORT)
        for track_id in visible_set:
            if track_id not in tracked_set:
                # Es un sujeto NUEVO
                self.subjects[track_id] = TrackedSubject(track_id)
            else:
                # Es un sujeto que ya conocíamos (sigue visible o regresa)
                self.subjects[track_id].mark_visible()

    def get_subject_info(self, track_id):
        """Obtiene el objeto de un sujeto para visualización."""
        return self.subjects.get(track_id)

    def get_final_summary(self) -> dict:
        """
        Prepara un diccionario con el resumen final de tiempos.
        Ya no imprime, solo devuelve los datos.
        """
        summary_data = {}

        if not self.subjects:
            # Devuelve un dict, no None
            return {"message": "No se trackeó ningún sujeto."}

        for track_id, subject in self.subjects.items():
            # Asegurarse de que el último tiempo visible se cuente si el app se cierra
            if subject.is_visible:
                subject.mark_invisible()

            # Convertimos los objetos 'datetime' y 'timedelta' a strings
            # porque JSON no puede guardarlos directamente.

            visible_str = str(subject.total_visible_time)
            invisible_str = str(subject.total_invisible_time)

            # 2. ¡LA SOLUCIÓN! Partir la cadena en el '.' y tomar solo la parte H:MM:SS
            visible_hms = visible_str.split('.')[0]
            invisible_hms = invisible_str.split('.')[0]

            summary_data[track_id] = {
                "Tiempo Visible Total": visible_hms,
                "Tiempo Invisible Total": invisible_hms,
                "Visto por última vez": subject.last_seen.isoformat() if subject.last_seen else None,
                "Desapareció por última vez": subject.last_disappeared.isoformat() if subject.last_disappeared else None
            }

        # Devuelve el diccionario completo
        return summary_data