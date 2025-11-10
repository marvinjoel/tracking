from app.database.TrackingRepository import TrackingRepository
from app.subject import TrackedSubject


class StateManager:
    """
    Esta clase gestiona la COLECCIÓN de sujetos.
    Actúa como un Patrón de Diseño "Manager" o "Repository" simple.
    No sabe de YOLO ni de SORT, solo recibe una lista de IDs.
    """

    def __init__(self, db_repo: TrackingRepository) -> None:
        self.subjects = {}
        self.db_repo = db_repo

    def update_states(self, visible_track_ids) -> None:
        """
        El "corazón" del programa. Sincroniza nuestro estado
        con lo que SORT acaba de ver en el frame actual.
        """
        visible_set = set(visible_track_ids)
        tracked_set = set(self.subjects.keys())

        # 1. Manejar sujetos que desaparecieron
        disappeared_ids = tracked_set - visible_set
        for track_id in disappeared_ids:
            if self.subjects[track_id].is_visible:
                self.subjects[track_id].mark_invisible()
                # Tarea Nueva: Registrar evento "PERDIDO"
                if self.db_repo:
                    self.db_repo.log_event(track_id, 'PERDIDO')

        # 2. Manejar sujetos nuevos o que siguen visibles
        for track_id in visible_set:
            if track_id not in tracked_set:
                # Es un sujeto NUEVO
                self.subjects[track_id] = TrackedSubject(track_id)
                # Tarea Nueva: Registrar evento "NUEVO"
                if self.db_repo:
                    self.db_repo.log_event(track_id, 'NUEVO')
            else:
                # Es un sujeto que ya conocíamos
                if not self.subjects[track_id].is_visible:
                    self.subjects[track_id].mark_visible()
                    # Tarea Nueva: Registrar evento "VISTO" (reaparece)
                    if self.db_repo:
                        self.db_repo.log_event(track_id, 'VISTO')
                else:
                    self.subjects[track_id].is_visible = True  # Sigue visible

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
            return {"message": "No se trackeó ningún sujeto."}

        for track_id, subject in self.subjects.items():
            if subject.is_visible:
                subject.mark_invisible()

            visible_str = str(subject.total_visible_time)
            invisible_str = str(subject.total_invisible_time)

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