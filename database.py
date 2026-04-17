import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv
from queue import Queue
from threading import Thread

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

CAMARA_ID = 1

# Cola de eventos
cola_db = Queue()

# Variables globales
conn = None
cur = None


def conectar():
    global conn, cur
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("[DB] Conectado a PostgreSQL")
    except Exception as e:
        print(f"[DB ERROR] No se pudo conectar: {e}")
        conn = None


def worker_db():
    global conn, cur

    conectar()
    if conn is None:
        return

    eventos_batch = []

    while True:
        evento = cola_db.get()

        if evento is None:
            break

        eventos_batch.append(evento)

        # Insertar cada 10 eventos (batch)
        if len(eventos_batch) >= 10:
            try:
                cur.executemany("""
                    INSERT INTO eventos_vehiculos
                    (camara_id, tipo, tipo_vehiculo, track_id, linea_cruzada, lado_origen, confianza, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, eventos_batch)

                conn.commit()
                eventos_batch.clear()

            except Exception as e:
                print(f"[DB ERROR] Batch fallo: {e}")

    # Insertar lo que quede antes de cerrar
    if eventos_batch:
        try:
            cur.executemany("""
                INSERT INTO eventos_vehiculos
                (camara_id, tipo, tipo_vehiculo, track_id, linea_cruzada, lado_origen, confianza, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, eventos_batch)
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Flush final fallo: {e}")

    cur.close()
    conn.close()
    print("[DB] Conexión cerrada")


def iniciar_worker():
    thread = Thread(target=worker_db, daemon=True)
    thread.start()
    return thread


def detener_worker(thread):
    cola_db.put(None)
    thread.join()


def registrar_evento(tipo, tipo_vehiculo, track_id, linea_cruzada, lado_origen, confianza):
    evento = (
        CAMARA_ID,
        tipo,
        tipo_vehiculo,
        track_id,
        linea_cruzada,
        lado_origen,
        round(confianza, 4),
        datetime.now()
    )

    cola_db.put(evento)