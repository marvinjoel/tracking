"""
Este archivo es el "mapa" central que le dice al manager
qué script de Python corresponde a cada nombre de algoritmo
en la base de datos.
"""

ALGORITHM_REGISTRY = {
    "person_tracking": "main.py",
    "box_counting": "box_counter.py",
    "license_plate_reader": "lpr.py"
}