# main.py
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
import json
import os

from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository
from app.state_manager import StateManager
from app.database.database_initializer import initialize_database



print("Cargando modelo YOLO...")
model = YOLO("yolov8m.pt")
print("Modelo YOLO cargado.")

tracker = DeepSort(
    max_age=300,
    n_init=10,
    nms_max_overlap=1.0,
    max_iou_distance=0.7,
    max_cosine_distance=0.7,
    nn_budget=None
)

# --- INICIALIZACIÓN DE COMPONENTES (EL ARREGLO) ---
# 1. Creamos la conexión
db_conn = DatabaseConnection()

# 2. Solo si la conexión es exitosa, procedemos
if db_conn.conn:
    # 3. Inicializamos las tablas (le pasamos el cursor)
    initialize_database(db_conn.cursor)

    # 4. Creamos el Repositorio (le pasamos el cursor)
    db_repo = TrackingRepository(db_conn.cursor)

    # 5. Inyectamos el Repositorio en el StateManager (DIP)
    state_manager = StateManager(db_repo=db_repo)
else:
    print("ADVERTENCIA: Corriendo sin conexión a base de datos.")
    state_smanager = StateManager(db_repo=None)  # Correr sin BD
# --- FIN DE INICIALIZACIÓN ---


video_path = 0
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: No se pudo abrir la fuente de video: {video_path}")
    if db_conn: db_conn.close()  # Asegurarnos de cerrar
    exit()

print("Iniciando captura de video...")

try:
    # --- Tu bucle principal ---
    while True:
        success, frame = cap.read()
        if not success:
            break  # Tu código es más limpio

        results_yolo = model(frame, classes=[0], verbose=False)

        detections_list = []
        MIN_CONFIDENCE = 0.7

        for box in results_yolo[0].boxes:
            cls = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())

            if cls == 0 and conf > MIN_CONFIDENCE:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                w = x2 - x1
                h = y2 - y1
                bbox_deepsort = [x1, y1, w, h]
                detections_list.append((bbox_deepsort, conf, cls))

        tracks = tracker.update_tracks(detections_list, frame=frame)

        visible_track_ids = []

        for track in tracks:
            if not track.is_confirmed() or track.time_since_update > 0:
                continue

            track_id = track.track_id
            visible_track_ids.append(track_id)

            bbox_tlbr = track.to_tlbr()
            x1, y1, x2, y2 = map(int, bbox_tlbr)

            subject = state_manager.get_subject_info(track_id)
            if subject:
                time_str = subject.get_visible_time_str()
                label = f"ID: {track_id} | T: {time_str}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

        # El StateManager ahora registra los eventos en la BD en tiempo real
        state_manager.update_states(visible_track_ids)

        cv2.imshow("MVP Tracking (pulsa 'q' para salir)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Cerrando stream...")
            break

finally:
    # --- Tu bloque 'finally' (CON EL ARREGLO) ---
    print("Cerrando recursos...")
    cap.release()
    cv2.destroyAllWindows()

    print("Obteniendo resumen final...")
    final_summary = state_manager.get_final_summary()

    # 1. Imprimir en Consola
    print("\n" + "=" * 30)
    print("--- RESUMEN FINAL DE TIEMPOS (Consola) ---")
    print("=" * 30)
    pretty_summary_string = json.dumps(final_summary, indent=4, ensure_ascii=False)
    print(pretty_summary_string)
    print("=" * 30)

    # 2. Guardar en Base de Datos
    if db_conn and db_conn.conn:
        # Reutilizamos el 'db_repo' creado al inicio
        db_repo_final = TrackingRepository(db_conn.cursor)
        db_repo_final.save_summary_data(final_summary)
        db_conn.close()  # Cerramos la conexión
    else:
        print("No se guardó en BD (conexión fallida al inicio).")

    # 3. Guardar JSON
    OUTPUT_DIR = "output"
    output_path = os.path.join(OUTPUT_DIR, "tracking_summary.json")
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=4, ensure_ascii=False)
        print(f"\nResumen final también guardado en: {output_path}\n")
    except Exception as e:
        print(f"Error al guardar el resumen JSON: {e}")