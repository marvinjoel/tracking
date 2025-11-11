from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import cv2
import json
import os
import time

# Importaciones de la app
from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository
from app.state_manager import StateManager
from app.database.database_initializer import initialize_database

# --- Variables Globales para el ROI ---
roi_pts = []  # Almacenará [(x1, y1), (x2, y2)]
drawing = False  # True si el usuario está arrastrando el ratón
roi_defined = False  # True si el ROI ya fue dibujado


# --- Fin ---

# --- Función de Callback del Ratón ---
def draw_roi_callback(event, x, y, flags, param):
    """
    Función que maneja los eventos del ratón para dibujar el ROI.
    """
    global roi_pts, drawing, roi_defined

    if event == cv2.EVENT_LBUTTONDOWN:
        # El usuario presionó el clic
        roi_pts = [(x, y)]
        drawing = True
        roi_defined = False

    elif event == cv2.EVENT_MOUSEMOVE:
        # El usuario está arrastrando
        if drawing:
            # Actualizamos el segundo punto en tiempo real
            if len(roi_pts) == 2:
                roi_pts[1] = (x, y)
            else:
                roi_pts.append((x, y))

    elif event == cv2.EVENT_LBUTTONUP:
        # El usuario soltó el clic
        drawing = False
        if len(roi_pts) == 2:
            # Nos aseguramos de que x1 < x2 y y1 < y2
            x1, y1 = roi_pts[0]
            x2, y2 = roi_pts[1]
            roi_pts = [(min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2))]
            roi_defined = True
            print(f"Región de Interés (ROI) definida en: {roi_pts}")


# --- Fin ---

# --- Función Asistente para el Filtro ---
def is_center_in_roi(bbox, roi):
    """
    Comprueba si el centro del bounding box (bbox) está dentro del roi.
    """
    x1, y1, x2, y2 = bbox
    roi_x1, roi_y1 = roi[0]
    roi_x2, roi_y2 = roi[1]

    # Calculamos el centro del bounding box
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    # Comprobamos si el centro está dentro de los límites del ROI
    return (roi_x1 <= center_x <= roi_x2) and (roi_y1 <= center_y <= roi_y2)


# --- Fin ---


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
    state_manager = StateManager(db_repo=db_repo)
else:
    print("ADVERTENCIA: Corriendo sin conexión a base de datos.")
    state_manager = StateManager(db_repo=None)
    db_repo = None
# --- FIN DE INICIALIZACIÓN ---

video_path = 0
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: No se pudo abrir la fuente de video: {video_path}")
    if db_conn: db_conn.close()
    exit()

WINDOW_NAME = "MVP Tracking (Arrastra para ROI, 'q' para salir)"
cv2.namedWindow(WINDOW_NAME)
cv2.setMouseCallback(WINDOW_NAME, draw_roi_callback)
print("\n--- INSTRUCCIONES ---")
print("Arrastra el ratón sobre la ventana para dibujar tu 'Región de Interés'.")
print("El sistema solo detectará personas dentro de esa región.")
print("---------------------\n")

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

            for box in results_yolo[0].boxes:
                cls = int(box.cls[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())

                # --- Lógica de Filtro ---
                # 1. Obtenemos el BBox (lo necesitamos para el filtro)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                # 2. Comprobamos si la detección está en el ROI
                is_in_roi = True  # Por defecto es True (si no hay ROI)
                if roi_defined:
                    is_in_roi = is_center_in_roi((x1, y1, x2, y2), roi_pts)

                # 3. Aplicamos TODOS los filtros
                if cls == 0 and conf > MIN_CONFIDENCE and is_in_roi:
                    # Solo si pasa todos los filtros, lo añadimos
                    w = x2 - x1;
                    h = y2 - y1
                    bbox_deepsort = [x1, y1, w, h]
                    detections_list.append((bbox_deepsort, conf, cls))
                # --- Fin [MODIFICADO] ---

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

            # --- Dibujar el ROI en el frame ---
            if roi_defined:
                # Dibuja el rectángulo del ROI (azul)
                cv2.rectangle(frame, roi_pts[0], roi_pts[1], (255, 0, 0), 2)
            elif drawing and len(roi_pts) == 2:
                # Dibuja el rectángulo (punteado) mientras se arrastra
                cv2.rectangle(frame, roi_pts[0], roi_pts[1], (0, 255, 255), 2)
            # --- Fin [NUEVO] ---

            cv2.imshow(WINDOW_NAME, frame)  # Usamos el nombre de ventana con callback

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