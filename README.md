# Sistema de Detección y Tracking con Control de Encendido/Apagado

Proyecto que detecta objetos en tiempo real con **YOLOv8**, realiza tracking y registra eventos de visibilidad (`NUEVO`, `VISTO`, `PERDIDO`) en PostgreSQL.

## Tecnologías

- YOLOv8 (Ultralytics) + tracker (BoT-SORT / ByteTrack)
- Python 3.9+
- OpenCV
- PostgreSQL
- Paquetes principales:
  - `ultralytics`
  - `opencv-python`
  - `psycopg2-binary`
  - `matplotlib` (para reportes y gráficos)

## Versión de YOLO

**YOLOv8** (Ultralytics). Modelos recomendados: `yolov8s.pt` o `yolov8m.pt`.

```bash
pip install ultralytics
```

*Compatible con YOLOv11 (solo cambiando el modelo).*

## Estructura del proyecto

```text
proyecto/
├── main.py                     # Programa principal: captura video, detecta, trackea y guarda eventos
├── generate_report.py          # Genera gráfico de línea de tiempo por track_id
├── app/
│   └── database/
│       ├── DatabaseConnection.py    # Conexión a PostgreSQL
│       └── TrackingRepository.py    # Operaciones en tabla de eventos
├── requirements.txt            # Dependencias
├── README.md                   # Este archivo
└── models/                     # (opcional) Modelos personalizados YOLO
```

## Base de datos (PostgreSQL)

### Tabla tracking_events

```sql
CREATE TABLE public.tracking_events (
    id SERIAL PRIMARY KEY,
    track_id INTEGER NOT NULL,
    timestamp_evento TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tipo_evento VARCHAR(20) NOT NULL 
        CHECK (tipo_evento IN ('NUEVO', 'VISTO', 'PERDIDO'))
);
```

### Tabla horarios_medicion

```sql
CREATE TABLE public.horarios_medicion (
    id SERIAL PRIMARY KEY,
    dia_semana INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),  -- 0 = lunes, 6 = domingo
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL
);
```

### Ejemplo de inserción de horarios

```sql
-- Lunes (0): 09:00 - 12:00
INSERT INTO public.horarios_medicion (dia_semana, hora_inicio, hora_fin)
VALUES (0, '09:00:00', '12:00:00');

-- Jueves (3): 14:00 - 18:00
INSERT INTO public.horarios_medicion (dia_semana, hora_inicio, hora_fin)
VALUES (3, '14:00:00', '18:00:00');
```

## Cómo ejecutar

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Iniciar el sistema

```bash
# Webcam local (índice 0)
python main.py --url 0 --camera_id 1

# Otra webcam
python main.py --url 1 --camera_id 2

# Cámara IP RTSP
python main.py --url "rtsp://usuario:contraseña@192.168.1.100:554/stream" --camera_id 3
```

### Generar reporte gráfico

```bash
python generate_report.py
```

*Te pedirá el track_id (el mismo camera_id que usaste).*

## Licencia

MIT License