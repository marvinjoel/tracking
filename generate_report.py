import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository


def calculate_time_blocks(events: list):
    """
    Toma la lista de eventos de la BD y la convierte en
    bloques de tiempo "visibles" e "invisibles".

    ESTA ES LA VERSIÓN CORREGIDA (v4)
    """
    blocks = []

    if len(events) < 2:
        print("Se necesitan al menos 2 eventos para dibujar un bloque.")
        return blocks

    # Iteramos sobre los eventos, parando en el PENÚLTIMO
    for i in range(len(events) - 1):

        # El evento actual define el INICIO y el ESTADO
        start_time = events[i][0]
        start_type = events[i][1]

        # El SIGUIENTE evento define el FIN
        end_time = events[i + 1][0]

        # Calculamos la duración de este bloque
        duration = end_time - start_time

        # Determinamos el color (estado) del bloque
        if start_type == 'NUEVO' or start_type == 'VISTO':
            status = 'visible'
        else:  # El tipo de inicio fue 'PERDIDO'
            status = 'invisible'

        # Añadimos el bloque completado a nuestra lista
        blocks.append((start_time, duration, status))

    print(f"Bloques de tiempo calculados: {len(blocks)}")
    return blocks

def plot_timeline(track_id, blocks):
    """
    Usa Matplotlib para dibujar el gráfico de barras horizontales (Gantt).
    """
    if not blocks:
        print(f"No se encontraron bloques de tiempo para el ID {track_id}.")
        return

    # Definimos los colores
    colors = {
        'visible': 'green',
        'invisible': 'red'
    }

    fig, ax = plt.subplots(figsize=(15, 4))

    local_tz = blocks[0][0].tzinfo

    for i, (start, duration, status) in enumerate(blocks):
        print(f"Dibujando bloque: {status} | Inicia: {start} | Dura: {duration}")

        width_in_days = duration.total_seconds() / (24 * 60 * 60)

        ax.barh(
            y=1,
            width=width_in_days,
            left=start,
            height=0.5,
            color=colors[status],
            label=status.capitalize() if i < 2 else ""
        )

    # --- Formateo y Estilo ---
    ax.set_yticks([])
    ax.set_title(f"Línea de Tiempo para el Track ID: {track_id}")
    ax.set_xlabel(f"Hora del Evento (Zona Horaria: {local_tz})")  # Añadimos la zona al label

    # --- 2. ¡LA CORRECCIÓN DE ZONA HORARIA! ---
    # Le decimos al formateador que USE la zona horaria local,
    # en lugar de convertir a UTC.
    formatter = mdates.DateFormatter('%H:%M:%S', tz=local_tz)
    ax.xaxis.set_major_formatter(formatter)
    # --- FIN DE LA CORRECCIÓN ---

    fig.autofmt_xdate()

    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[s]) for s in ['visible', 'invisible']]
    labels = ['Tiempo Visible', 'Tiempo Invisible']
    ax.legend(handles, labels, loc='lower center')

    plt.tight_layout()
    plt.show()


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

    print("Generando gráfico...")
    plot_timeline(track_id_input, time_blocks)

    db_conn.close()


if __name__ == "__main__":
    main()