import cv2
from ultralytics import YOLO
from collections import defaultdict
import time

from database import registrar_evento, iniciar_worker, detener_worker

# ─── Configuración ─────────────────────────────────────────────
MODEL_PATH   = "yolov8n.pt"
CAMARA       = 0
CONFIANZA    = 0.4
CLASES       = [2, 5, 7]

LINEA_A = 500
LINEA_B = 950
COOLDOWN_SEGUNDOS = 3

ultimo_cruce = defaultdict(lambda: {"A": 0, "B": 0})

# ─── Inicializar ───────────────────────────────────────────────
model = YOLO(MODEL_PATH)
cap   = cv2.VideoCapture(CAMARA)

if not cap.isOpened():
    print("Error: No se pudo acceder a la cámara.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

track_history = defaultdict(list)
NOMBRES = {2: "Auto", 5: "Bus", 7: "Camion"}
COLORES = {2: (0, 200, 255), 5: (255, 165, 0), 7: (180, 100, 255)}

print("Sistema de detección activo. Registrando eventos...")

# 🔥 Iniciar hilo DB
thread_db = iniciar_worker()

# ─── Funciones ────────────────────────────────────────────────
def cruzo_linea_vertical(historial, x_linea):
    if len(historial) < 2:
        return False
    prev_x = historial[-2][0]
    curr_x = historial[-1][0]
    return (prev_x < x_linea <= curr_x) or (prev_x > x_linea >= curr_x)


def evaluar_cruce_A(track_id, historial, nombre, confianza):
    if len(historial) < 2:
        return

    ahora = time.time()
    if ahora - ultimo_cruce[track_id]["A"] < COOLDOWN_SEGUNDOS:
        return

    ultimo_cruce[track_id]["A"] = ahora
    prev_x = historial[-2][0]

    accion = "entrada" if prev_x < LINEA_A else "salida"

    registrar_evento(accion, nombre.lower(), track_id, "A", "izq", confianza)


def evaluar_cruce_B(track_id, historial, nombre, confianza):
    if len(historial) < 2:
        return

    ahora = time.time()
    if ahora - ultimo_cruce[track_id]["B"] < COOLDOWN_SEGUNDOS:
        return

    ultimo_cruce[track_id]["B"] = ahora
    prev_x = historial[-2][0]

    accion = "entrada" if prev_x > LINEA_B else "salida"

    registrar_evento(accion, nombre.lower(), track_id, "B", "der", confianza)


# ─── Loop principal ────────────────────────────────────────────
while True:
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(
        frame,
        persist=True,
        classes=CLASES,
        conf=CONFIANZA,
        tracker="bytetrack.yaml",
        verbose=False
    )

    h, w = frame.shape[:2]

    # Líneas
    cv2.line(frame, (LINEA_A, 0), (LINEA_A, h), (0, 165, 255), 2)
    cv2.line(frame, (LINEA_B, 0), (LINEA_B, h), (200, 0, 200), 2)

    # Zona sombreada
    overlay = frame.copy()
    cv2.rectangle(overlay, (LINEA_A, 0), (LINEA_B, h), (200, 200, 200), -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes      = results[0].boxes.xywh.cpu()
        track_ids  = results[0].boxes.id.int().cpu().tolist()
        clases_det = results[0].boxes.cls.int().cpu().tolist()
        confs      = results[0].boxes.conf.cpu().tolist()

        for box, track_id, clase_id, confianza in zip(boxes, track_ids, clases_det, confs):
            cx, cy = float(box[0]), float(box[1])
            w_box, h_box = float(box[2]), float(box[3])

            track_history[track_id].append((cx, cy))
            if len(track_history[track_id]) > 40:
                track_history[track_id].pop(0)

            historial = track_history[track_id]

            nombre = NOMBRES.get(clase_id, "Vehiculo")
            color  = COLORES.get(clase_id, (255, 255, 255))

            if cruzo_linea_vertical(historial, LINEA_A):
                evaluar_cruce_A(track_id, historial, nombre, confianza)

            if cruzo_linea_vertical(historial, LINEA_B):
                evaluar_cruce_B(track_id, historial, nombre, confianza)

            # Bounding box
            x1, y1 = int(cx - w_box/2), int(cy - h_box/2)
            x2, y2 = int(cx + w_box/2), int(cy + h_box/2)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{nombre} #{track_id}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.putText(frame, "Q: Salir", (w - 80, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

    cv2.imshow("Deteccion de Vehiculos", frame)

# ─── Cierre ───────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()

detener_worker(thread_db)