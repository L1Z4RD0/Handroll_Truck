"""
Pruebas unitarias para las funciones de control_acceso.py

Se hace mock de todas las dependencias pesadas de nivel de módulo (YOLO, cv2,
database) para poder importar y probar las funciones puras de forma aislada
sin necesidad de cámara, GPU ni base de datos.
"""

import sys
import time
import types
import unittest
from collections import defaultdict
from unittest.mock import MagicMock, patch, call


# ──────────────────────────────────────────────────────────────────────────────
# Bloquear imports pesados ANTES de importar control_acceso
# ──────────────────────────────────────────────────────────────────────────────

# Mock de cv2
cv2_mock = MagicMock()
cv2_mock.VideoCapture.return_value.isOpened.return_value = True
cv2_mock.CAP_PROP_FRAME_WIDTH  = 3
cv2_mock.CAP_PROP_FRAME_HEIGHT = 4
sys.modules["cv2"] = cv2_mock

# Mock de ultralytics
ultralytics_mock = types.ModuleType("ultralytics")
ultralytics_mock.YOLO = MagicMock(return_value=MagicMock())
sys.modules["ultralytics"] = ultralytics_mock

# Mock del módulo database completo
database_mock = types.ModuleType("database")
database_mock.registrar_evento  = MagicMock()
database_mock.iniciar_worker    = MagicMock(return_value=MagicMock())
database_mock.detener_worker    = MagicMock()
sys.modules["database"] = database_mock

# Evitar que el bloque `while True` se ejecute al importar
# (se parchea waitKey para que devuelva 'q' de inmediato)
cv2_mock.waitKey.return_value = ord("q") & 0xFF

# ──────────────────────────────────────────────────────────────────────────────
# Ahora sí importamos las funciones que queremos probar
# ──────────────────────────────────────────────────────────────────────────────
# Usamos importlib para poder recargar el módulo con los mocks activos
import importlib

# Parchear cap.read() para que retorne False y corte el loop de inmediato
cv2_mock.VideoCapture.return_value.read.return_value = (False, None)

import control_acceso as ca


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES locales (mismas que en control_acceso.py)
# ──────────────────────────────────────────────────────────────────────────────
LINEA_A = 500
LINEA_B = 950
COOLDOWN_SEGUNDOS = 3


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: cruzo_linea_vertical
# ══════════════════════════════════════════════════════════════════════════════
class TestCruzaLineaVertical(unittest.TestCase):
    """Pruebas para cruzo_linea_vertical(historial, x_linea)."""

    # ── Historial insuficiente ────────────────────────────────────────────────

    def test_historial_vacio_retorna_false(self):
        """Con historial vacío no puede haber cruce."""
        self.assertFalse(ca.cruzo_linea_vertical([], 500))

    def test_historial_un_punto_retorna_false(self):
        """Con un solo punto no existe punto anterior; no hay cruce."""
        self.assertFalse(ca.cruzo_linea_vertical([(300, 100)], 500))

    # ── Cruce izquierda → derecha ─────────────────────────────────────────────

    def test_cruce_izq_a_der_exacto(self):
        """El vehículo pasa exactamente por la línea de izq a der."""
        historial = [(499, 100), (500, 100)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, 500))

    def test_cruce_izq_a_der_sobrepasa(self):
        """El vehículo cruza la línea y continúa hacia la derecha."""
        historial = [(100, 200), (600, 200)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, 500))

    # ── Cruce derecha → izquierda ─────────────────────────────────────────────

    def test_cruce_der_a_izq_exacto(self):
        """El vehículo pasa exactamente por la línea de der a izq."""
        historial = [(501, 100), (500, 100)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, 500))

    def test_cruce_der_a_izq_sobrepasa(self):
        """El vehículo cruza la línea y continúa hacia la izquierda."""
        historial = [(800, 200), (300, 200)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, 500))

    # ── Sin cruce ─────────────────────────────────────────────────────────────

    def test_sin_cruce_ambos_a_la_izquierda(self):
        """Ambos puntos están a la izquierda de la línea; no hay cruce."""
        historial = [(100, 100), (400, 100)]
        self.assertFalse(ca.cruzo_linea_vertical(historial, 500))

    def test_sin_cruce_ambos_a_la_derecha(self):
        """Ambos puntos están a la derecha de la línea; no hay cruce."""
        historial = [(600, 100), (800, 100)]
        self.assertFalse(ca.cruzo_linea_vertical(historial, 500))

    def test_sin_cruce_vehiculo_estatico(self):
        """El vehículo no se mueve; no hay cruce."""
        historial = [(300, 100), (300, 100)]
        self.assertFalse(ca.cruzo_linea_vertical(historial, 500))

    # ── Sólo los dos últimos puntos importan ──────────────────────────────────

    def test_usa_solo_los_dos_ultimos_puntos(self):
        """El historial puede tener muchos puntos; sólo los 2 últimos cuentan."""
        historial = [(50, 0), (100, 0), (200, 0), (400, 0), (600, 0)]
        # Los dos últimos: (400, 0) → (600, 0) → cruce en 500
        self.assertTrue(ca.cruzo_linea_vertical(historial, 500))

    def test_historial_largo_sin_cruce_reciente(self):
        """Muchos puntos, pero los 2 últimos no cruzan la línea."""
        historial = [(100, 0), (200, 0), (600, 0), (700, 0), (800, 0)]
        # Los dos últimos: (700, 0) → (800, 0) → ambos a la derecha
        self.assertFalse(ca.cruzo_linea_vertical(historial, 500))

    # ── Líneas en posiciones extremas ─────────────────────────────────────────

    def test_linea_en_x_cero(self):
        """Línea en x=0: cruce siempre desde la derecha."""
        historial = [(10, 0), (0, 0)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, 0))

    def test_linea_en_posicion_linea_B(self):
        """Verifica cruce en la posición real de LINEA_B (950)."""
        historial = [(900, 100), (1000, 100)]
        self.assertTrue(ca.cruzo_linea_vertical(historial, LINEA_B))

    def test_no_cruce_justo_antes_de_linea(self):
        """El vehículo avanza pero se queda justo antes de la línea."""
        historial = [(400, 100), (499, 100)]
        self.assertFalse(ca.cruzo_linea_vertical(historial, 500))


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: evaluar_cruce_A
# ══════════════════════════════════════════════════════════════════════════════
class TestEvaluarCruceA(unittest.TestCase):
    """Pruebas para evaluar_cruce_A(track_id, historial, nombre, confianza)."""

    def setUp(self):
        """Resetear el estado global entre pruebas."""
        ca.ultimo_cruce.clear()
        database_mock.registrar_evento.reset_mock()

    # ── Historial insuficiente ────────────────────────────────────────────────

    def test_historial_un_punto_no_registra(self):
        """Con un solo punto en el historial no se debe registrar nada."""
        ca.evaluar_cruce_A(1, [(300, 100)], "Auto", 0.9)
        database_mock.registrar_evento.assert_not_called()

    def test_historial_vacio_no_registra(self):
        """Con historial vacío no se debe registrar nada."""
        ca.evaluar_cruce_A(1, [], "Auto", 0.9)
        database_mock.registrar_evento.assert_not_called()

    # ── Dirección del cruce ───────────────────────────────────────────────────

    def test_entrada_cuando_viene_de_la_izquierda(self):
        """prev_x < LINEA_A → acción 'entrada'."""
        historial = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        ca.evaluar_cruce_A(10, historial, "Bus", 0.85)
        database_mock.registrar_evento.assert_called_once_with(
            "entrada", "bus", 10, "A", "izq", 0.85
        )

    def test_salida_cuando_viene_de_la_derecha(self):
        """prev_x > LINEA_A → acción 'salida'."""
        historial = [(LINEA_A + 50, 100), (LINEA_A - 1, 100)]
        ca.evaluar_cruce_A(20, historial, "Camion", 0.75)
        database_mock.registrar_evento.assert_called_once_with(
            "salida", "camion", 20, "A", "izq", 0.75
        )

    def test_nombre_se_pasa_en_minuscula(self):
        """El nombre del vehículo debe enviarse en minúsculas a registrar_evento."""
        historial = [(LINEA_A - 10, 100), (LINEA_A + 10, 100)]
        ca.evaluar_cruce_A(30, historial, "Auto", 0.9)
        args = database_mock.registrar_evento.call_args[0]
        self.assertEqual(args[1], "auto")  # índice 1 = tipo_vehiculo

    # ── Cooldown ──────────────────────────────────────────────────────────────

    def test_cooldown_bloquea_segundo_cruce(self):
        """Un segundo cruce dentro del período de cooldown no debe registrarse."""
        historial = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        ca.evaluar_cruce_A(40, historial, "Auto", 0.9)
        ca.evaluar_cruce_A(40, historial, "Auto", 0.9)
        self.assertEqual(database_mock.registrar_evento.call_count, 1)

    def test_cooldown_permite_cruce_despues_de_espera(self):
        """Un cruce posterior al cooldown SÍ debe registrarse."""
        historial = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        # Primer cruce
        ca.evaluar_cruce_A(50, historial, "Auto", 0.9)
        # Simular que ya pasó el cooldown
        ca.ultimo_cruce[50]["A"] = time.time() - COOLDOWN_SEGUNDOS - 1
        # Segundo cruce
        ca.evaluar_cruce_A(50, historial, "Auto", 0.9)
        self.assertEqual(database_mock.registrar_evento.call_count, 2)

    def test_cooldown_independiente_por_track_id(self):
        """El cooldown de un vehículo no afecta a otro con diferente track_id."""
        historial = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        ca.evaluar_cruce_A(60, historial, "Auto", 0.9)
        ca.evaluar_cruce_A(61, historial, "Bus", 0.8)
        self.assertEqual(database_mock.registrar_evento.call_count, 2)

    def test_cooldown_linea_A_no_afecta_linea_B(self):
        """El cooldown de línea A no afecta al cooldown de línea B del mismo track."""
        historial = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        ca.evaluar_cruce_A(70, historial, "Auto", 0.9)
        # El cooldown en "A" no debe afectar evaluar_cruce_B
        historial_b = [(LINEA_B - 1, 100), (LINEA_B + 1, 100)]
        ca.evaluar_cruce_B(70, historial_b, "Auto", 0.9)
        self.assertEqual(database_mock.registrar_evento.call_count, 2)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: evaluar_cruce_B
# ══════════════════════════════════════════════════════════════════════════════
class TestEvaluarCruceB(unittest.TestCase):
    """Pruebas para evaluar_cruce_B(track_id, historial, nombre, confianza)."""

    def setUp(self):
        ca.ultimo_cruce.clear()
        database_mock.registrar_evento.reset_mock()

    # ── Historial insuficiente ────────────────────────────────────────────────

    def test_historial_un_punto_no_registra(self):
        """Con un solo punto en el historial no se debe registrar nada."""
        ca.evaluar_cruce_B(1, [(1000, 100)], "Bus", 0.9)
        database_mock.registrar_evento.assert_not_called()

    def test_historial_vacio_no_registra(self):
        ca.evaluar_cruce_B(1, [], "Bus", 0.9)
        database_mock.registrar_evento.assert_not_called()

    # ── Dirección del cruce (lógica invertida respecto a A) ────────────────────

    def test_entrada_cuando_viene_de_la_derecha(self):
        """prev_x > LINEA_B → acción 'entrada' (entra desde la derecha)."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(10, historial, "Camion", 0.80)
        database_mock.registrar_evento.assert_called_once_with(
            "entrada", "camion", 10, "B", "der", 0.80
        )

    def test_salida_cuando_viene_de_la_izquierda(self):
        """prev_x <= LINEA_B → acción 'salida' (sale hacia la derecha)."""
        historial = [(LINEA_B - 10, 100), (LINEA_B + 10, 100)]
        ca.evaluar_cruce_B(20, historial, "Auto", 0.95)
        database_mock.registrar_evento.assert_called_once_with(
            "salida", "auto", 20, "B", "der", 0.95
        )

    def test_nombre_se_pasa_en_minuscula(self):
        """El nombre del vehículo debe enviarse en minúsculas."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(30, historial, "Bus", 0.7)
        args = database_mock.registrar_evento.call_args[0]
        self.assertEqual(args[1], "bus")

    def test_linea_correcta_es_B(self):
        """El argumento linea_cruzada debe ser 'B'."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(31, historial, "Auto", 0.9)
        args = database_mock.registrar_evento.call_args[0]
        self.assertEqual(args[3], "B")

    def test_lado_origen_es_der(self):
        """El argumento lado_origen debe ser 'der'."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(32, historial, "Auto", 0.9)
        args = database_mock.registrar_evento.call_args[0]
        self.assertEqual(args[4], "der")

    # ── Cooldown ──────────────────────────────────────────────────────────────

    def test_cooldown_bloquea_segundo_cruce(self):
        """Un segundo cruce inmediato del mismo vehículo en B no se registra."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(40, historial, "Auto", 0.9)
        ca.evaluar_cruce_B(40, historial, "Auto", 0.9)
        self.assertEqual(database_mock.registrar_evento.call_count, 1)

    def test_cooldown_permite_cruce_despues_de_espera(self):
        """Un cruce posterior al tiempo de cooldown sí se registra."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(50, historial, "Bus", 0.9)
        ca.ultimo_cruce[50]["B"] = time.time() - COOLDOWN_SEGUNDOS - 1
        ca.evaluar_cruce_B(50, historial, "Bus", 0.9)
        self.assertEqual(database_mock.registrar_evento.call_count, 2)

    def test_cooldown_independiente_por_track_id(self):
        """El cooldown de distintos vehículos en B es independiente."""
        historial = [(LINEA_B + 10, 100), (LINEA_B - 10, 100)]
        ca.evaluar_cruce_B(60, historial, "Auto", 0.9)
        ca.evaluar_cruce_B(61, historial, "Bus", 0.8)
        self.assertEqual(database_mock.registrar_evento.call_count, 2)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS: Integración entre cruzo_linea_vertical + evaluar_cruce_*
# ══════════════════════════════════════════════════════════════════════════════
class TestIntegracionCruceCompleto(unittest.TestCase):
    """
    Verifica que la combinación de cruzo_linea_vertical + evaluar_cruce_*
    refleja el flujo real del bucle principal de control_acceso.
    """

    def setUp(self):
        ca.ultimo_cruce.clear()
        database_mock.registrar_evento.reset_mock()

    def test_flujo_completo_cruce_linea_A_entrada(self):
        """Simula un vehículo cruzando la línea A de izq a der (entrada)."""
        historial = [(LINEA_A - 5, 100), (LINEA_A + 5, 100)]
        if ca.cruzo_linea_vertical(historial, LINEA_A):
            ca.evaluar_cruce_A(1, historial, "Auto", 0.90)
        database_mock.registrar_evento.assert_called_once_with(
            "entrada", "auto", 1, "A", "izq", 0.90
        )

    def test_flujo_completo_cruce_linea_B_salida(self):
        """Simula un vehículo cruzando la línea B de izq a der (salida)."""
        historial = [(LINEA_B - 5, 100), (LINEA_B + 5, 100)]
        if ca.cruzo_linea_vertical(historial, LINEA_B):
            ca.evaluar_cruce_B(2, historial, "Camion", 0.77)
        database_mock.registrar_evento.assert_called_once_with(
            "salida", "camion", 2, "B", "der", 0.77
        )

    def test_sin_cruce_no_llama_evaluar(self):
        """Si no hay cruce, no se debe llamar a registrar_evento."""
        historial = [(100, 100), (200, 100)]  # Ambos lejos de LINEA_A
        if ca.cruzo_linea_vertical(historial, LINEA_A):
            ca.evaluar_cruce_A(3, historial, "Bus", 0.88)
        database_mock.registrar_evento.assert_not_called()

    def test_vehiculo_cruza_ambas_lineas(self):
        """
        Un vehículo en movimiento lento puede cruzar primero A y luego B;
        ambos eventos deben registrarse.
        """
        historial_a = [(LINEA_A - 1, 100), (LINEA_A + 1, 100)]
        historial_b = [(LINEA_B - 1, 100), (LINEA_B + 1, 100)]

        if ca.cruzo_linea_vertical(historial_a, LINEA_A):
            ca.evaluar_cruce_A(5, historial_a, "Auto", 0.91)

        if ca.cruzo_linea_vertical(historial_b, LINEA_B):
            ca.evaluar_cruce_B(5, historial_b, "Auto", 0.91)

        self.assertEqual(database_mock.registrar_evento.call_count, 2)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
