import cv2
from ultralytics import YOLO
from collections import defaultdict
import time
from database import registrar_evento

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
    print("No se pudo abrir la cámara. Verifica que Iriun está conectado.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

track_history    = defaultdict(list)
contador_entrada = 0
contador_salida  = 0

NOMBRES = {2: "Auto", 5: "Bus", 7: "Camion"}
COLORES = {2: (0, 200, 255), 5: (255, 165, 0), 7: (180, 100, 255)}

print("Sistema iniciado con Iriun Webcam.")
print("Presiona Q para salir | ESPACIO para pausar | R para resetear contadores")
pausado = False

# ─── Funciones de cruce ────────────────────────────────────────
def cruzo_linea_vertical(historial, x_linea):
    if len(historial) < 2:
        return False
    prev_x = historial[-2][0]
    curr_x = historial[-1][0]
    return (prev_x < x_linea <= curr_x) or (prev_x > x_linea >= curr_x)

def evaluar_cruce_A(track_id, historial, nombre, confianza):
    global contador_entrada, contador_salida
    if len(historial) < 2:
        return
    ahora = time.time()
    if ahora - ultimo_cruce[track_id]["A"] < COOLDOWN_SEGUNDOS:
        return
    ultimo_cruce[track_id]["A"] = ahora
    prev_x        = historial[-2][0]
    tipo_vehiculo = nombre.lower()
    if prev_x < LINEA_A:
        contador_entrada += 1
        print(f"[ENTRADA] {nombre} ID:{track_id} vino de calle izq | Total entradas: {contador_entrada}")
        registrar_evento("entrada", tipo_vehiculo, track_id, "A", "izq", confianza)
    else:
        contador_salida += 1
        print(f"[SALIDA]  {nombre} ID:{track_id} salió por izq     | Total salidas:  {contador_salida}")
        registrar_evento("salida", tipo_vehiculo, track_id, "A", "izq", confianza)

def evaluar_cruce_B(track_id, historial, nombre, confianza):
    global contador_entrada, contador_salida
    if len(historial) < 2:
        return
    ahora = time.time()
    if ahora - ultimo_cruce[track_id]["B"] < COOLDOWN_SEGUNDOS:
        return
    ultimo_cruce[track_id]["B"] = ahora
    prev_x        = historial[-2][0]
    tipo_vehiculo = nombre.lower()
    if prev_x > LINEA_B:
        contador_entrada += 1
        print(f"[ENTRADA] {nombre} ID:{track_id} vino de calle der | Total entradas: {contador_entrada}")
        registrar_evento("entrada", tipo_vehiculo, track_id, "B", "der", confianza)
    else:
        contador_salida += 1
        print(f"[SALIDA]  {nombre} ID:{track_id} salió por der     | Total salidas:  {contador_salida}")
        registrar_evento("salida", tipo_vehiculo, track_id, "B", "der", confianza)

# ─── Loop principal ────────────────────────────────────────────
while True:
    tecla = cv2.waitKey(1) & 0xFF
    if tecla == ord("q"):
        break
    elif tecla == ord(" "):
        pausado = not pausado
        print("PAUSADO" if pausado else "REANUDADO")
    elif tecla == ord("r"):
        contador_entrada = 0
        contador_salida  = 0
        track_history.clear()
        ultimo_cruce.clear()
        print("Contadores reseteados.")

    if pausado:
        continue

    ret, frame = cap.read()
    if not ret:
        print("No se recibe imagen. Verifica la conexión de Iriun.")
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

    cv2.line(frame, (LINEA_A, 0), (LINEA_A, h), (0, 165, 255), 2)
    cv2.line(frame, (LINEA_B, 0), (LINEA_B, h), (200, 0, 200), 2)
    cv2.putText(frame, "A (calle izq)", (LINEA_A + 6, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    cv2.putText(frame, "B (calle der)", (LINEA_B + 6, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 0, 200), 2)

    overlay = frame.copy()
    cv2.rectangle(overlay, (LINEA_A, 0), (LINEA_B, h), (200, 200, 200), -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    if results[0].boxes is not None and results[0].boxes.id is not None:
        boxes      = results[0].boxes.xywh.cpu()
        track_ids  = results[0].boxes.id.int().cpu().tolist()
        clases_det = results[0].boxes.cls.int().cpu().tolist()
        confianzas = results[0].boxes.conf.cpu().tolist()

        for box, track_id, clase_id, confianza in zip(boxes, track_ids, clases_det, confianzas):
            x, y, w_box, h_box = box
            cx, cy = float(x), float(y)

            track_history[track_id].append((cx, cy))
            if len(track_history[track_id]) > 40:
                track_history[track_id].pop(0)

            historial = track_history[track_id]
            color     = COLORES.get(clase_id, (255, 255, 255))
            nombre    = NOMBRES.get(clase_id, "Vehiculo")

            if cruzo_linea_vertical(historial, LINEA_A):
                evaluar_cruce_A(track_id, historial, nombre, confianza)

            if cruzo_linea_vertical(historial, LINEA_B):
                evaluar_cruce_B(track_id, historial, nombre, confianza)

            x1, y1 = int(cx - w_box/2), int(cy - h_box/2)
            x2, y2 = int(cx + w_box/2), int(cy + h_box/2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{nombre} ID:{track_id}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.rectangle(frame, (8, 8), (310, 130), (0, 0, 0), -1)
    cv2.putText(frame, f"Entradas: {contador_entrada}", (15, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(frame, f"Salidas:  {contador_salida}",  (15, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 100, 255), 2)
    cv2.putText(frame, "Q=salir  SPC=pausa  R=reset", (15, 118),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    cv2.imshow("Control de Acceso - Vehiculos", frame)

# ─── Cierre ────────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()
print(f"\nResumen final → Entradas: {contador_entrada} | Salidas: {contador_salida}")