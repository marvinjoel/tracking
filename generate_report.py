# generate_report.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository


def calculate_time_blocks(events: list):
    """
    Toma la lista de eventos de la BD y la convierte en
    bloques de tiempo "visibles" e "invisibles".
    """
    blocks = []
    start_time = None
    last_status = None

    for event_time, event_type in events:

        if event_type == 'NUEVO' or event_type == 'VISTO':
            if last_status == 'PERDIDO':
                # Si estaba 'PERDIDO' y ahora es 'VISTO', cerramos el bloque 'PERDIDO'
                end_time = event_time
                duration = end_time - start_time
                blocks.append((start_time, duration, 'invisible'))

            # Iniciamos un nuevo bloque 'VISTO'
            start_time = event_time
            last_status = 'VISTO'

        elif event_type == 'PERDIDO':
            if last_status == 'VISTO':
                # Si estaba 'VISTO' y ahora es 'PERDIDO', cerramos el bloque 'VISTO'
                end_time = event_time
                duration = end_time - start_time
                blocks.append((start_time, duration, 'visible'))

            # Iniciamos un nuevo bloque 'PERDIDO'
            start_time = event_time
            last_status = 'PERDIDO'

    # Al final, cerramos el último bloque que haya quedado abierto
    if start_time and last_status:
        # --- ¡ESTA ES LA CORRECCIÓN! ---
        # Usamos .astimezone() para que la hora actual TAMBIÉN
        # tenga información de zona horaria (sea "aware").
        end_time = datetime.now().astimezone()
        # --- FIN DE LA CORRECCIÓN ---

        duration = end_time - start_time
        color = 'visible' if last_status == 'VISTO' else 'invisible'
        blocks.append((start_time, duration, color))

    return blocks


def plot_timeline(track_id, blocks):
    """
    Usa Matplotlib para dibujar el gráfico de barras horizontales (Gantt).
    """
    if not blocks:
        print(f"No se encontraron bloques de tiempo para el ID {track_id}.")
        return

    # Definimos los colores para tu tarea
    colors = {
        'visible': 'green',
        'invisible': 'red'
    }

    # Creamos la figura
    fig, ax = plt.subplots(figsize=(15, 4))

    # Iteramos sobre los bloques y los dibujamos
    for i, (start, duration, status) in enumerate(blocks):
        # Usamos barh (barra horizontal)
        # 'y' es la posición (ej. 1), 'width' es la duración, 'left' es dónde empieza
        ax.barh(
            y=1,
            width=duration,
            left=start,
            height=0.5,
            color=colors[status],
            label=status.capitalize() if i < 2 else ""  # Solo para la leyenda
        )

    # --- Formateo y Estilo ---
    ax.set_yticks([])  # Ocultamos el eje Y (solo es una barra)
    ax.set_title(f"Línea de Tiempo para el Track ID: {track_id}")
    ax.set_xlabel("Hora del Evento")

    # Formatear el eje X para que muestre la hora H:MM:SS
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    fig.autofmt_xdate()  # Rota las fechas para que no se solapen

    # Creamos una leyenda
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[s]) for s in ['visible', 'invisible']]
    labels = ['Tiempo Visible', 'Tiempo Invisible']
    ax.legend(handles, labels)

    plt.tight_layout()
    plt.show()  # ¡Mostramos el gráfico!


def main():
    """
    Función principal para orquestar el reporte.
    """
    track_id_input = input("Por favor, ingrese el Track ID para generar el gráfico: ")
    if not track_id_input:
        print("No se ingresó un ID.")
        return

    print("Conectando a la base de datos...")
    db_conn = DatabaseConnection()

    if not db_conn.conn:
        print("No se pudo conectar a la base de datos. Abortando.")
        return

    db_repo = TrackingRepository(db_conn.cursor)

    print(f"Buscando eventos para el ID: {track_id_input}...")
    events = db_repo.get_events_by_track_id(track_id_input)

    if not events:
        print(f"No se encontraron eventos para el ID {track_id_input} en la base de datos.")
        db_conn.close()
        return

    print(f"Procesando {len(events)} eventos...")
    time_blocks = calculate_time_blocks(events)

    # 5. Generar el gráfico
    print("Generando gráfico...")
    plot_timeline(track_id_input, time_blocks)

    db_conn.close()


if __name__ == "__main__":
    main()