import subprocess
import time
import sys
from app.database.DatabaseConnection import DatabaseConnection
from app.database.TrackingRepository import TrackingRepository
from app.utils.algorithm_registry import ALGORITHM_REGISTRY

running_processes = {}
CHECK_INTERVAL = 30


def launch_camera_process(camera_id, url_rtsp, algorithm):
    """
    Lanza un nuevo proceso 'main.py' para una cámara específica.
    """
    global running_processes

    cam_id_str = str(camera_id)

    script_to_run: str = ALGORITHM_REGISTRY.get(algorithm)

    if not script_to_run:
        print(f"--- MANAGER: Error: Algoritmo '{algorithm}' desconocido para ID {camera_id}. No se puede lanzar. ---")
        return

    command = [
        sys.executable,
        script_to_run,
        "--url", url_rtsp,
        "--camera_id", cam_id_str
    ]

    print(f"--- MANAGER: Iniciando proceso para Cámara ID {cam_id_str} ---")
    print(f"--- MANAGER: Comando: {' '.join(command)} ---")

    try:
        process = subprocess.Popen(command)
        running_processes[camera_id] = process
        print(f"--- MANAGER: Proceso para Cámara ID {cam_id_str} iniciado (PID: {process.pid}) ---")
    except Exception as e:
        print(f"--- MANAGER: ERROR al iniciar Cámara ID {cam_id_str}: {e} ---")


def poll_camera_processes():
    """
    Revisa si alguno de los procesos que lanzamos ha muerto (crasheado).
    Si es así, lo elimina del diccionario para que el manager intente relanzarlo.
    """
    global running_processes

    dead_cameras = []
    for camera_id, process in running_processes.items():
        if process.poll() is not None:
            print(f"--- MANAGER: ¡ALERTA! Proceso para Cámara ID {camera_id} (PID: {process.pid}) ha terminado. ---")
            dead_cameras.append(camera_id)

    for camera_id in dead_cameras:
        del running_processes[camera_id]


def main_manager_loop():
    """
    El bucle principal del orquestador.
    """
    print("Iniciando Orquestador Multi-Cámara (Manager)...")

    while True:
        try:
            print(f"\n--- MANAGER: Chequeando Base de Datos (próximo chequeo en {CHECK_INTERVAL}s) ---")
            db_conn = DatabaseConnection()

            if not db_conn.conn:
                print("--- MANAGER: ERROR: No se pudo conectar a la BD. Reintentando... ---")
                time.sleep(CHECK_INTERVAL)
                continue

            db_repo = TrackingRepository(db_conn.cursor)

            active_cameras_in_db = db_repo.get_active_cameras()
            active_cam_ids_in_db = set()

            for (camera_id, url_rtsp, algorithm) in active_cameras_in_db:

                active_cam_ids_in_db.add(camera_id)

                if camera_id not in running_processes:
                    print(f"--- MANAGER: Se detectó una nueva cámara activa: ID {camera_id} ---")
                    launch_camera_process(camera_id, url_rtsp, algorithm)

            running_cam_ids = set(running_processes.keys())
            cameras_to_stop = running_cam_ids - active_cam_ids_in_db

            for camera_id in cameras_to_stop:
                print(f"--- MANAGER: Se detectó cámara inactiva: ID {camera_id}. Deteniendo proceso... ---")
                process = running_processes[camera_id]
                process.terminate()
                del running_processes[camera_id]

            poll_camera_processes()

            db_conn.close()
            print(f"--- MANAGER: Chequeo completo. Durmiendo {CHECK_INTERVAL} segundos... ---")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n--- MANAGER: Detectado Ctrl+C. Cerrando todos los procesos... ---")
            for camera_id, process in running_processes.items():
                print(f"--- MANAGER: Deteniendo Cámara ID {camera_id} (PID: {process.pid}) ---")
                process.terminate()
            break
        except Exception as e:
            print(f"--- MANAGER: ERROR INESPERADO en el bucle principal: {e} ---")
            time.sleep(10)


if __name__ == "__main__":
    main_manager_loop()