from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
import json
import os
import time

from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository
from app.state_manager import StateManager
from app.database.database_initializer import initialize_database

print("Cargando modelo YOLO...")
model = YOLO("yolov8m.pt")
print("Modelo YOLO cargado.")

# Configuración del Tracker (Tu código - SIN CAMBIOS)
tracker = DeepSort(
    max_age=300,
    n_init=10,
    nms_max_overlap=1.0,
    max_iou_distance=0.7,
    max_cosine_distance=0.7,
    nn_budget=None
)

db_conn = DatabaseConnection()

if db_conn.conn:
    initialize_database(db_conn.cursor)
    db_repo = TrackingRepository(db_conn.cursor)
    state_manager = StateManager(db_repo=db_repo)
else:
    print("ADVERTENCIA: Corriendo sin conexión a base de datos.")
    # ¡CORRECCIÓN DE BUG! (Tu código decía 'state_smanager')
    state_manager = StateManager(db_repo=None)
    db_repo = None


video_path = 0
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: No se pudo abrir la fuente de video: {video_path}")
    if db_conn: db_conn.close()
    exit()

print("Iniciando bucle principal...")

is_window_visible = False

try:
    while True:

        # 1. Chequeamos si tenemos conexión y si el horario está activo
        # (Si no hay db_repo, asumimos que debe correr siempre)
        is_active = not db_repo or db_repo.is_schedule_active()

        if is_active:
            # --- MODO ACTIVO ---
            if not is_window_visible:
                print("Horario ACTIVO. Iniciando monitoreo...")
                is_window_visible = True

            success, frame = cap.read()
            if not success:
                break

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

            state_manager.update_states(visible_track_ids)
            cv2.imshow("MVP Tracking (pulsa 'q' para salir)", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Cerrando stream...")
                break

        else:
            # --- MODO INACTIVO ---
            if is_window_visible:
                # Si la ventana estaba abierta, la cerramos
                print("Horario INACTIVO. Pausando monitoreo...")
                cv2.destroyWindow("MVP Tracking (pulsa 'q' para salir)")
                is_window_visible = False

            # "Dormimos" por 30 segundos antes de volver a chequear
            time.sleep(30)

finally:
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
        # Volvemos a crear un repo para el resumen final
        db_repo_final = TrackingRepository(db_conn.cursor)
        db_repo_final.save_summary_data(final_summary)
        db_conn.close()
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