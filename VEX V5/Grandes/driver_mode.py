# ================================================================
# VEXcode – Configuración y Teleoperado (Robot con llantas mecanum)
# ---------------------------------------------------------------
# Descripción:
#   Control de un robot con tren motriz de 4 motores (mecanum) y
#   actuadores adicionales: rampa, cepillo, garra y pinza.
#
#   • Conducción tipo arcade:
#       - Axis3: avance/retroceso
#       - Axis4: strafe lateral (izquierda/derecha)
#   • Strafe forzado (botones):
#       - LEFT / RIGHT: strafe a velocidad fija (50%)
#   • Rampa:
#       - Axis2: modo manual (cuando el modo AUTO está apagado)
#       - Botón B: alterna modo rampa AUTO (RPM fijo) / MANUAL
#   • Cepillo:
#       - Botón A: alterna encendido/apagado
#   • Garra:
#       - L1 abre (FORWARD), R1 cierra (REVERSE) con retención
#   • Pinza:
#       - L2 abre (FORWARD), R2 cierra (REVERSE) con retención
#
# Notas:
#   - Usa zona muerta (DEADZONE) para ignorar ruido del joystick.
#   - El valor de RPM para rampa en AUTO es 470 RPM.
#   - Ajusta inversión (reversa) de motores según cableado real.
#
# Autor: @deepdevjose - github.com/deepdevjose
# ================================================================

from vex import *

# ------------------------------------------------
# Inicialización del cerebro y controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# Constantes de configuración
# ------------------------------------------------
DEADZONE = 10  # Umbral para ignorar pequeños valores del joystick (ruido)

# ------------------------------------------------
# Motores del tren motriz (mecanum)
#   Ajusta el tercer parámetro (invertido) si tu robot se mueve al revés.
# ------------------------------------------------
motor_back_left   = Motor(Ports.PORT12, GearSetting.RATIO_18_1, True)   # Izquierdo trasero
motor_back_right  = Motor(Ports.PORT2,  GearSetting.RATIO_18_1, False)  # Derecho trasero
motor_front_left  = Motor(Ports.PORT1,  GearSetting.RATIO_18_1, False)  # Izquierdo delantero
motor_front_right = Motor(Ports.PORT11, GearSetting.RATIO_18_1, True)   # Derecho delantero

# ------------------------------------------------
# Otros actuadores
# ------------------------------------------------
motor_rampa            = Motor(Ports.PORT10, GearSetting.RATIO_6_1,  False)
motor_cepillo          = Motor(Ports.PORT20, GearSetting.RATIO_36_1, False)
motor_garra_open_close = Motor(Ports.PORT19, GearSetting.RATIO_36_1, False)
motor_pinza_open_close = Motor(Ports.PORT6,  GearSetting.RATIO_36_1, False)

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
modo_rampa_auto = False     # True = AUTO (RPM fija); False = manual con Axis2
prev_ButtonB    = False     # Flanco para toggle de rampa
cepillo_on      = False     # Estado ON/OFF del cepillo
prev_ButtonA    = False     # Flanco para toggle del cepillo

# ================================================================
# Funciones de movimiento (Tren motriz)
# ================================================================
def mover_adelante(velocidad: int) -> None:
    """Mueve el robot hacia adelante a 'velocidad' (%)."""
    motor_back_left.spin(FORWARD,  velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def mover_atras(velocidad: int) -> None:
    """Mueve el robot hacia atrás a 'velocidad' (%)."""
    motor_back_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def girar_izquierda(velocidad: int) -> None:
    """Giro en su lugar hacia la izquierda (diferencial)."""
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(FORWARD,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(REVERSE,  velocidad, PERCENT)

def girar_derecha(velocidad: int) -> None:
    """Giro en su lugar hacia la derecha (diferencial)."""
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(REVERSE,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(FORWARD,   velocidad, PERCENT)

def girarc_izquierda(velocidad: int) -> None:
    """Movimiento lateral (strafe) hacia la izquierda con llantas mecanum."""
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(REVERSE,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD,  velocidad, PERCENT)

def girarc_derecha(velocidad: int) -> None:
    """Movimiento lateral (strafe) hacia la derecha con llantas mecanum."""
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(FORWARD,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(REVERSE,   velocidad, PERCENT)

def detener() -> None:
    """Detiene los cuatro motores del tren motriz."""
    motor_back_left.stop()
    motor_back_right.stop()
    motor_front_left.stop()
    motor_front_right.stop()

# ================================================================
# Funciones de control de actuadores (Rampa, Garra, Pinza, Cepillo)
# ================================================================
def control_rampa_manual() -> None:
    """
    Control MANUAL de la rampa con Axis2.
    - Aplica DEADZONE para evitar movimientos involuntarios.
    - Mantiene proporción de velocidad con el valor del joystick.
    """
    value = controller.axis2.position()
    if abs(value) < DEADZONE:
        motor_rampa.stop()
    else:
        direction = FORWARD if value > 0 else REVERSE
        motor_rampa.spin(direction, abs(value), PERCENT)

def aplicar_rampa_auto() -> None:
    """
    Control AUTO de la rampa.
    - Fija la velocidad a 470 RPM y gira en sentido FORWARD.
    - Ajusta RPM según tu mecánica real si es necesario.
    """
    motor_rampa.set_velocity(470, RPM)
    motor_rampa.spin(FORWARD)

def toggle_rampa_mode() -> None:
    """
    Alterna entre modo de rampa AUTO/MANUAL con flanco del botón B.
    - Usa 'prev_ButtonB' para evitar rebotes (toggle por pulsación).
    """
    global modo_rampa_auto, prev_ButtonB
    if controller.buttonB.pressing() and not prev_ButtonB:
        modo_rampa_auto = not modo_rampa_auto
    prev_ButtonB = controller.buttonB.pressing()

def control_garra_gradual() -> None:
    """
    Control de la garra con retención (HOLD):
    - L1: abre (FORWARD) al 60%
    - R1: cierra (REVERSE) al 60%
    - Sin pulsación: mantiene posición (HOLD)
    """
    if controller.buttonL1.pressing():
        motor_garra_open_close.spin(FORWARD, 60, PERCENT)
    elif controller.buttonR1.pressing():
        motor_garra_open_close.spin(REVERSE, 60, PERCENT)
    else:
        motor_garra_open_close.stop(HOLD)

def control_pinza_gradual() -> None:
    """
    Control de la pinza con retención (HOLD):
    - L2: abre (FORWARD) al 100%
    - R2: cierra (REVERSE) al 100%
    - Sin pulsación: mantiene posición (HOLD)
    """
    if controller.buttonL2.pressing():
        motor_pinza_open_close.spin(FORWARD, 100, PERCENT)
    elif controller.buttonR2.pressing():
        motor_pinza_open_close.spin(REVERSE, 100, PERCENT)
    else:
        motor_pinza_open_close.stop(HOLD)

def girar_cepillo() -> None:
    """
    Toggle ON/OFF del cepillo con botón A usando flanco:
    - ON: gira en REVERSE al 100%
    - OFF: se detiene
    """
    global cepillo_on, prev_ButtonA
    if controller.buttonA.pressing() and not prev_ButtonA:
        cepillo_on = not cepillo_on
        if cepillo_on:
            motor_cepillo.spin(REVERSE, 100, PERCENT)
        else:
            motor_cepillo.stop()
    prev_ButtonA = controller.buttonA.pressing()

# ================================================================
# Conducción – Arcade (Axis3 avance/retro, Axis4 strafe)
# ================================================================
def control_drive() -> None:
    """
    Control principal de conducción tipo arcade:
      - Axis3: avance (+) / retroceso (–)
      - Axis4: strafe derecha (+) / izquierda (–)
    Prioridad:
      1) Si hay strafe (Axis4 ≠ 0), se mueve lateralmente.
      2) Si no hay strafe pero hay avance (Axis3 ≠ 0), avanza/retrocede.
      3) Si no hay entradas activas, detiene el tren motriz.
    """
    # Lectura de ejes
    axis_forward = controller.axis3.position()  # Adelante / Atrás
    axis_strafe  = controller.axis4.position()  # Izquierda / Derecha (strafe)

    # Zona muerta
    if abs(axis_forward) < DEADZONE:
        axis_forward = 0
    if abs(axis_strafe) < DEADZONE:
        axis_strafe = 0

    # 1) Strafe tiene prioridad
    if axis_strafe > 0:
        # Strafe a la derecha
        motor_front_left.spin(FORWARD,   axis_strafe, PERCENT)
        motor_back_left.spin(REVERSE,    axis_strafe, PERCENT)
        motor_front_right.spin(REVERSE,  axis_strafe, PERCENT)
        motor_back_right.spin(FORWARD,   axis_strafe, PERCENT)

    elif axis_strafe < 0:
        # Strafe a la izquierda
        speed = abs(axis_strafe)
        motor_front_left.spin(REVERSE,  speed, PERCENT)
        motor_back_left.spin(FORWARD,   speed, PERCENT)
        motor_front_right.spin(FORWARD, speed, PERCENT)
        motor_back_right.spin(REVERSE,  speed, PERCENT)

    # 2) Avance/retro si no hay strafe
    elif axis_forward > 0:
        mover_adelante(axis_forward)
    elif axis_forward < 0:
        mover_atras(abs(axis_forward))
    # 3) Sin entradas -> detener
    else:
        detener()

# ================================================================
# Bucle principal (Teleoperado)
# ================================================================
def main() -> None:
    """
    Bucle teleoperado:
      - Alterna/aplica modo rampa AUTO/MANUAL.
      - Actualiza cepillo, pinza y garra.
      - Actualiza movimiento base (arcade).
      - Botones LEFT/RIGHT fuerzan strafe a 50% (útil para ajustes finos).
      - Espera 20 ms para no saturar CPU.
    """
    while True:
        # Rampa
        toggle_rampa_mode()
        if modo_rampa_auto:
            aplicar_rampa_auto()
        else:
            control_rampa_manual()

        # Actuadores
        girar_cepillo()
        control_pinza_gradual()
        control_garra_gradual()

        # Movimiento base
        control_drive()

        # Strafe forzado
        if controller.buttonLeft.pressing():
            girarc_izquierda(50)
        elif controller.buttonRight.pressing():
            girarc_derecha(50)

        # Pequeña pausa para estabilidad
        wait(20, MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()
