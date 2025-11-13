import os
import cv2
from datetime import datetime
from app.utils.roi_manager import get_roi_coordinates


def save_proof_image(frame, track_id):
    """
    Guarda el frame actual como prueba de ausencia.
    """
    try:
        roi_coords = get_roi_coordinates()
        if roi_coords:
            x1, y1, x2, y2 = roi_coords
            margin = 20
            frame_h, frame_w = frame.shape[:2]
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(frame_w, x2 + margin)
            y2 = min(frame_h, y2 + margin)

            cropped_frame = frame[y1:y2, x1:x2]
            if cropped_frame.size == 0:
                print(
                    f"ADVERTENCIA: ROI inválido o demasiado pequeño para el recorte. Guardando frame completo para ID {track_id}.")
                frame_to_save = frame
            else:
                frame_to_save = cropped_frame
        else:
            frame_to_save = frame

        proof_dir = os.path.join("output", "proof_images", f"ID_{track_id}")
        os.makedirs(proof_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{timestamp}_PERDIDO.jpg"
        filepath = os.path.join(proof_dir, filename)

        cv2.imwrite(filepath, frame_to_save)
    except Exception as e:
        print(f"ERROR: No se pudo guardar la imagen de prueba: {e}")