import cv2

roi_pts = []
drawing = False
roi_defined = False


def draw_roi_callback(event, x, y, flags, param):
    """
    Función que maneja los eventos del ratón para dibujar el ROI.
    """
    global roi_pts, drawing, roi_defined

    if event == cv2.EVENT_LBUTTONDOWN:
        roi_pts = [(x, y)]
        drawing = True
        roi_defined = False
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            if len(roi_pts) == 2:
                roi_pts[1] = (x, y)
            else:
                roi_pts.append((x, y))
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        if len(roi_pts) == 2:
            x1, y1 = roi_pts[0]
            x2, y2 = roi_pts[1]
            roi_pts = [(min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2))]
            roi_defined = True
            print(f"Región de Interés (ROI) definida en: {roi_pts}")


def is_center_in_roi(bbox, roi):
    """
    Comprueba si el centro del bounding box (bbox) está dentro del roi.
    """
    x1, y1, x2, y2 = bbox
    roi_x1, roi_y1 = roi[0]
    roi_x2, roi_y2 = roi[1]
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    return (roi_x1 <= center_x <= roi_x2) and (roi_y1 <= center_y <= roi_y2)


def draw_roi_on_frame(frame):
    """
    Dibuja el rectángulo del ROI en el frame.
    """
    global roi_pts, drawing, roi_defined
    if roi_defined:
        cv2.rectangle(frame, roi_pts[0], roi_pts[1], (255, 0, 0), 2)
    elif drawing and len(roi_pts) == 2:
        cv2.rectangle(frame, roi_pts[0], roi_pts[1], (0, 255, 255), 2)

    return frame  # Devuelve el frame modificado


def get_roi_state():
    """Devuelve el estado actual del ROI para el filtro."""
    global roi_defined, roi_pts
    return roi_defined, roi_pts

def get_roi_coordinates():
    """
    Devuelve las coordenadas del ROI si está definido, None en caso contrario.
    Formato: (x1, y1, x2, y2)
    """
    global roi_defined, roi_pts
    if roi_defined and len(roi_pts) == 2:
        x1, y1 = roi_pts[0]
        x2, y2 = roi_pts[1]
        return (x1, y1, x2, y2)
    return None