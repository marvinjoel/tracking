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