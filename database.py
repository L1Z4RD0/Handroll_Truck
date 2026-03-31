import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

CAMARA_ID = 1

def conectar():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"[DB ERROR] No se pudo conectar: {e}")
        return None

def registrar_evento(tipo, tipo_vehiculo, track_id, linea_cruzada, lado_origen, confianza):
    conn = conectar()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO eventos_vehiculos
                (camara_id, tipo, tipo_vehiculo, track_id, linea_cruzada, lado_origen, confianza, timestamp)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            CAMARA_ID,
            tipo,
            tipo_vehiculo,
            track_id,
            linea_cruzada,
            lado_origen,
            round(confianza, 4),
            datetime.now()
        ))
        conn.commit()
        print(f"[DB] Evento guardado: {tipo} | {tipo_vehiculo} | ID:{track_id}")
    except Exception as e:
        print(f"[DB ERROR] No se pudo insertar: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    conn = conectar()
    if conn:
        print("Conexión exitosa a PostgreSQL")
        conn.close()