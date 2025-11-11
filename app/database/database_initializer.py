
def initialize_database(cursor):
    """
     única responsabilidad es crear/verificar
    el esquema (las tablas) de la base de datos.
    """
    if not cursor:
        return

    # 1. Tabla de Resumen
    create_summary_table_query = """
    CREATE TABLE IF NOT EXISTS tracking_summary (
        id SERIAL PRIMARY KEY,
        track_id VARCHAR(50) NOT NULL,
        tiempo_visible_total_str VARCHAR(50),
        tiempo_invisible_total_str VARCHAR(50),
        last_seen_timestamp TIMESTAMPTZ,
        last_disappeared_timestamp TIMESTAMPTZ,
        run_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_summary_table_query)
    print("Tabla 'tracking_summary' verificada/creada.")

    create_events_table_query = """
    CREATE TABLE IF NOT EXISTS tracking_events (
        id SERIAL PRIMARY KEY,
        track_id VARCHAR(50) NOT NULL,
        timestamp_evento TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        tipo_evento VARCHAR(10) NOT NULL 
    );
    """
    cursor.execute(create_events_table_query)
    print("Tabla 'tracking_events' (de movimiento) verificada/creada.")

    create_schedule_table_query = """
    CREATE TABLE IF NOT EXISTS horarios_medicion (
        id SERIAL PRIMARY KEY,
        
        -- 0=Lunes, 1=Martes, ..., 6=Domingo
        dia_semana INT NOT NULL, 
        
        hora_inicio TIME NOT NULL, -- Ej: '09:00:00'
        hora_fin TIME NOT NULL     -- Ej: '12:00:00'
    );
    """
    cursor.execute(create_schedule_table_query)
    print("Tabla 'horarios_medicion' verificada/creada.")