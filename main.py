from ultralytics import YOLO
from state_manager import StateManager
from deep_sort_realtime.deepsort_tracker import DeepSort
from app.database import TrackingRepository
import cv2
import json
import os

print("Cargando modelo YOLO...")
model = YOLO("yolov8m.pt")
print("Modelo YOLO cargado.")

tracker = DeepSort(
    # Aumentamos la paciencia a 10 segundos (300 frames @ 30fps)
    max_age=300,

    # [FIX 2] Aumentamos el "costo" de crear un NUEVO ID.
    # El tracker debe ver un objeto por 10 frames antes de
    # asignarle un ID nuevo. Esto le da a la Re-ID más tiempo
    # para encontrar una coincidencia con un ID antiguo.
    n_init=10,

    nms_max_overlap=1.0,
    max_iou_distance=0.7,

    # [FIX 2] Hacemos la Re-ID aún más flexible
    max_cosine_distance=0.7,

    nn_budget=None
)

# Inicializar nuestro Gestor de Estado
state_manager = StateManager()

db_repo = TrackingRepository()

video_path = 0
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: No se pudo abrir la fuente de video: {video_path}")
    exit()

print("Iniciando captura de video...")

try:
    # --- Iniciar Bucle Principal ---
    while True:
        success, frame = cap.read()
        if not success:
            print("Fin del video o error al leer frame.")
            break

        # --- 3. FORMATO DE DETECCIÓN ---
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

        # --- 4. LLAMADA DE UPDATE ---
        tracks = tracker.update_tracks(detections_list, frame=frame)

        # --- 5. LECTURA DE RESULTADOS ---
        visible_track_ids = []

        for track in tracks:
            # --- [FIX 1 - "Ghosting"] ---
            # Si 'time_since_update' > 0, significa que el track
            # se está basando en una PREDICCIÓN (es un "fantasma").
            # Lo ignoramos para que el cuadro desaparezca al instante.
            if not track.is_confirmed() or track.time_since_update > 0:
                continue

            track_id = track.track_id
            visible_track_ids.append(track_id)

            bbox_tlbr = track.to_tlbr()
            x1, y1, x2, y2 = map(int, bbox_tlbr)

            # --- DIBUJO ---
            subject = state_manager.get_subject_info(track_id)
            if subject:
                time_str = subject.get_visible_time_str()
                label = f"ID: {track_id} | T: {time_str}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

        # --- 6. ACTUALIZACIÓN DEL "CEREBRO" ---
        state_manager.update_states(visible_track_ids)

        # Mostrar el frame
        cv2.imshow("MVP Tracking (pulsa 'q' para salir)", frame)

        # Salir con la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Cerrando stream...")
            break

finally:
    # --- PASO 9: Limpiar y Guardar Métricas (No cambia nada) ---
    print("Cerrando recursos...")
    cap.release()
    cv2.destroyAllWindows()

    print("Obteniendo resumen final...")
    final_summary = state_manager.get_final_summary()

    # --- 1. Imprimir en Consola ---
    print("\n" + "=" * 30)
    print("--- RESUMEN FINAL DE TIEMPOS (Consola) ---")
    print("=" * 30)
    pretty_summary_string = json.dumps(final_summary, indent=4, ensure_ascii=False)
    print(pretty_summary_string)
    print("=" * 30)

    # --- 2. Guardar en Base de Datos (¡NUEVO!) ---
    # En lugar de guardar en JSON, llamamos a nuestro repositorio.
    if db_repo.conn:  # Solo si la conexión fue exitosa
        db_repo.save_summary_data(final_summary)
        db_repo.close()
    else:
        print("No se guardó en BD (conexión fallida al inicio).")

    # --- 2. Guardar en Archivo JSON ---
    OUTPUT_DIR = "output"
    output_path = os.path.join(OUTPUT_DIR, "tracking_summary.json")

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=4, ensure_ascii=False)
        print(f"\nResumen final también guardado en: {output_path}\n")

    except Exception as e:
        print(f"Error al guardar el resumen JSON: {e}")