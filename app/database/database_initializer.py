
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