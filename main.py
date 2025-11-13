import cv2
import json
import os
import time
import argparse

from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository
from app.database.database_initializer import initialize_database
from deep_sort_realtime.deepsort_tracker import DeepSort
from app.state_manager import StateManager
from app.utils.image_saver import save_proof_image
from app.utils.roi_manager import (
    draw_roi_callback,
    is_center_in_roi,
    draw_roi_on_frame,
    get_roi_state
)
from ultralytics import YOLO
from dotenv import load_dotenv


load_dotenv()

parser = argparse.ArgumentParser(description="Inicia el tracker en una cámara.")
parser.add_argument(
    "--url",
    required=True,
    help="La URL RTSP de la cámara, '0' para webcam, o una ruta a un video."
)
parser.add_argument(
    "--camera_id",
    required=True,
    help="El ID de la cámara (de la tabla lista_camaras) para asociar los eventos."
)
args = parser.parse_args()

video_source = args.url
if video_source.isdigit():
    video_path = int(video_source)
else:
    video_path = video_source

camera_id_para_eventos = args.camera_id
print(f"Iniciando tracker para la Cámara ID: {camera_id_para_eventos} (Fuente: {video_path})")


print("Cargando modelo YOLO...")
model = YOLO("yolov8m.pt")
print("Modelo YOLO cargado.")

tracker = DeepSort(
    max_age=300, n_init=10, nms_max_overlap=1.0,
    max_iou_distance=0.7, max_cosine_distance=0.7, nn_budget=None
)

# --- INICIALIZACIÓN DE COMPONENTES ---
db_conn = DatabaseConnection()
if db_conn.conn:
    initialize_database(db_conn.cursor)
    db_repo = TrackingRepository(db_conn.cursor)
    state_manager = StateManager(db_repo=db_repo, camera_id=camera_id_para_eventos)
else:
    print("ADVERTENCIA: Corriendo sin conexión a base de datos.")
    state_manager = StateManager(db_repo=None, camera_id="default")
    db_repo = None
# --- FIN DE INICIALIZACIÓN ---

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: No se pudo abrir la fuente de video: {video_path}")
    if db_conn: db_conn.close()
    exit()

# --- Configuración de la Ventana ---
WINDOW_NAME = "MVP Tracking (Arrastra para ROI, 'q' para salir)"
cv2.namedWindow(WINDOW_NAME)
cv2.setMouseCallback(WINDOW_NAME, draw_roi_callback)  # Conecta el callback
print("\n--- INSTRUCCIONES ---")
print("Arrastra el ratón sobre la ventana para dibujar tu 'Región de Interés'.")
print("---------------------\n")
# --- Fin ---

is_window_visible = False

try:
    while True:
        is_active = not db_repo or db_repo.is_schedule_active()

        if is_active:
            if not is_window_visible:
                print("Horario ACTIVO. Iniciando monitoreo...")
                is_window_visible = True

            success, frame = cap.read()
            if not success:
                break

            results_yolo = model(frame, classes=[0], verbose=False)

            detections_list = []
            MIN_CONFIDENCE = 0.7

            roi_defined, roi_pts = get_roi_state()

            for box in results_yolo[0].boxes:
                cls = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                is_in_roi = True
                if roi_defined:
                    is_in_roi = is_center_in_roi((x1, y1, x2, y2), roi_pts)

                if cls == 0 and conf > MIN_CONFIDENCE and is_in_roi:
                    w = x2 - x1;
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

            # 6. ACTUALIZACIÓN DEL "CEREBRO"
            disappeared_ids = state_manager.update_states(visible_track_ids)

            # TAREA NUEVA: Guardar Pruebas de Ausencia
            if disappeared_ids:
                for track_id in disappeared_ids:
                    print(f"ID {track_id} ha desaparecido. Guardando prueba...")
                    save_proof_image(frame, track_id)

            # Dibujar el ROI en el frame
            frame = draw_roi_on_frame(frame)

            cv2.imshow(WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Cerrando stream...")
                break

        else:
            # --- MODO INACTIVO ---
            if is_window_visible:
                print("Horario INACTIVO. Pausando monitoreo...")
                cv2.destroyWindow(WINDOW_NAME)
                is_window_visible = False
            time.sleep(30)

finally:
    # (Tu bloque finally - SIN CAMBIOS)
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