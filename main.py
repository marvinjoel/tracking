from ultralytics import YOLO
from state_manager import StateManager
from sort import SortTracker as Sort
import numpy as np
import cv2
import json
import os


print("Cargando modelo YOLO...")
model = YOLO("yolov8n.pt")
print("Modelo YOLO cargado.")

tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)

# Inicializar nuestro Gestor de Estado
state_manager = StateManager()

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

        results = model(frame, classes=[0], verbose=False)

        detections_list = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = box.conf[0].cpu().numpy()
            cls = box.cls[0].cpu().numpy()
            detections_list.append([x1, y1, x2, y2, conf, cls])

        detections_np = np.array(detections_list)

        trackers = tracker.update(detections_np, frame)

        # --- FIN DE LA CORRECCIÓN ---

        visible_track_ids = [int(d[4]) for d in trackers]

        state_manager.update_states(visible_track_ids)

        # --- PASO 8: Visualizar Detecciones y Métricas ---
        for d in trackers:
            x1, y1, x2, y2, track_id = map(int, d[:5])

            # Obtener la info del sujeto desde nuestro "cerebro"
            subject = state_manager.get_subject_info(track_id)

            if subject:
                # Obtener el string de tiempo formateado
                time_str = subject.get_visible_time_str()
                label = f"ID: {track_id} | T: {time_str}"

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)

                # Poner el texto del ID y Tiempo
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

        # Mostrar el frame
        cv2.imshow("MVP Tracking (pulsa 'q' para salir)", frame)

        # Salir con la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Cerrando stream...")
            break

finally:
    # --- PASO 9: Limpiar y Guardar Métricas Finales ---
    print("Cerrando recursos...")
    cap.release()
    cv2.destroyAllWindows()

    # Obtener los datos del resumen desde el state_manager
    print("Obteniendo resumen final...")
    final_summary = state_manager.get_final_summary()

    # --- 1. Imprimir en Consola ---
    # Usamos json.dumps() (con 's' de string) para 'pretty-print'
    # el diccionario a la consola.
    print("\n" + "=" * 30)
    print("--- RESUMEN FINAL DE TIEMPOS (Consola) ---")
    print("=" * 30)

    # json.dumps() convierte el dict en un string JSON formateado
    pretty_summary_string = json.dumps(final_summary, indent=4, ensure_ascii=False)
    print(pretty_summary_string)

    print("=" * 30)

    # --- 2. Guardar en Archivo JSON ---
    OUTPUT_DIR = "output"
    output_path = os.path.join(OUTPUT_DIR, "tracking_summary.json")

    try:
        # Crear la carpeta 'output' si no existe
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # json.dump() (sin 's') guarda el dict en el archivo
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_summary, f, indent=4, ensure_ascii=False)

        print(f"\nResumen final también guardado en: {output_path}\n")

    except Exception as e:
        print(f"Error al guardar el resumen JSON: {e}")