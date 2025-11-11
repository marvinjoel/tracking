import os
import cv2
from datetime import datetime

def save_proof_image(frame, track_id):
    """
    Guarda el frame actual como prueba de ausencia.
    """
    try:
        proof_dir = os.path.join("output", "proof_images", f"ID_{track_id}")
        os.makedirs(proof_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{timestamp}_PERDIDO.jpg"
        filepath = os.path.join(proof_dir, filename)
        cv2.imwrite(filepath, frame)
    except Exception as e:
        print(f"ERROR: No se pudo guardar la imagen de prueba: {e}")