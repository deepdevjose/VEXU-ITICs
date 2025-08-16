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
#   • Rampa:
#       - Axis2: manual
#       - Botón B: alterna modo rampa AUTO (370 RPM) / MANUAL
#   • Cepillo:
#       - Botón A: alterna encendido/apagado
#   • Garra:
#       - L1 abre (FORWARD), R1 cierra (REVERSE) con retención
#   • Pinza:
#       - L2 abre (FORWARD), R2 cierra (REVERSE) con retención
#
# Notas:
#   - Usa zona muerta (DEADZONE) para ignorar ruido del joystick.
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
# Motores del tren motriz (mecanum)
# ------------------------------------------------
motor_back_left   = Motor(Ports.PORT19, GearSetting.RATIO_18_1, True)   # Izquierdo trasero
motor_back_right  = Motor(Ports.PORT20, GearSetting.RATIO_18_1, False)  # Derecho trasero
motor_front_left  = Motor(Ports.PORT17, GearSetting.RATIO_18_1, False)  # Izquierdo delantero
motor_front_right = Motor(Ports.PORT16, GearSetting.RATIO_18_1, True)   # Derecho delantero

# ------------------------------------------------
# Otros actuadores
# ------------------------------------------------
motor_rampa            = Motor(Ports.PORT11, GearSetting.RATIO_6_1, True)
motor_cepillo          = Motor(Ports.PORT10, GearSetting.RATIO_18_1, False)
motor_garra_open_close = Motor(Ports.PORT12, GearSetting.RATIO_36_1, False)
motor_pinza_open_close = Motor(Ports.PORT14, GearSetting.RATIO_36_1, False)

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
cepillo_on      = False   # Estado ON/OFF del cepillo
prev_ButtonA    = False   # Flanco de botón A

modo_rampa_auto = False   # Estado AUTO/MANUAL de rampa
prev_ButtonB    = False   # Flanco de botón B

DEADZONE = 5  # Umbral para ignorar ruido de joystick

# ================================================================
# Funciones de Movimiento (Tren motriz)
# ================================================================
def mover_adelante(velocidad: int) -> None:
    """Mueve el robot hacia adelante a 'velocidad' (%)."""
    motor_back_left.spin(REVERSE, velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def mover_atras(velocidad: int) -> None:
    """Mueve el robot hacia atrás a 'velocidad' (%)."""
    motor_back_left.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def girar_izquierda(velocidad: int) -> None:
    """Gira sobre su eje hacia la izquierda."""
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(REVERSE,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD,  velocidad, PERCENT)

def girar_derecha(velocidad: int) -> None:
    """Gira sobre su eje hacia la derecha."""
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(FORWARD,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(REVERSE,   velocidad, PERCENT)

def girarc_izquierda(velocidad: int) -> None:
    """Movimiento lateral (strafe) hacia la izquierda con mecanum."""
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(REVERSE,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD,  velocidad, PERCENT)

def girarc_derecha(velocidad: int) -> None:
    """Movimiento lateral (strafe) hacia la derecha con mecanum."""
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(FORWARD,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(REVERSE,   velocidad, PERCENT)

def detener() -> None:
    """Detiene todos los motores del tren motriz."""
    motor_back_left.stop()
    motor_back_right.stop()
    motor_front_left.stop()
    motor_front_right.stop()

# ================================================================
# Funciones de Control (Rampa, Garra, Pinza, Cepillo)
# ================================================================
def control_drive() -> None:
    """
    Control arcade:
      - Axis3 = avance/retroceso
      - Axis4 = strafe lateral
    """
    axis_forward = controller.axis3.position()
    axis_strafe  = controller.axis4.position()

    # Aplicar zona muerta
    if abs(axis_forward) < DEADZONE:
        axis_forward = 0
    if abs(axis_strafe) < DEADZONE:
        axis_strafe = 0

    # Strafe tiene prioridad
    if axis_strafe > 0:
        motor_front_left.spin(FORWARD,   axis_strafe, PERCENT)
        motor_back_left.spin(REVERSE,    axis_strafe, PERCENT)
        motor_front_right.spin(REVERSE,  axis_strafe, PERCENT)
        motor_back_right.spin(FORWARD,   axis_strafe, PERCENT)

    elif axis_strafe < 0:
        speed = abs(axis_strafe)
        motor_front_left.spin(REVERSE,  speed, PERCENT)
        motor_back_left.spin(FORWARD,   speed, PERCENT)
        motor_front_right.spin(FORWARD, speed, PERCENT)
        motor_back_right.spin(REVERSE,  speed, PERCENT)

    elif axis_forward > 0:
        mover_adelante(axis_forward)
    elif axis_forward < 0:
        mover_atras(abs(axis_forward))
    else:
        detener()

def control_rampa() -> None:
    """Control manual de la rampa con Axis2."""
    value = controller.axis2.value()
    if abs(value) < DEADZONE:
        motor_rampa.stop()
    else:
        direction = REVERSE if value > 0 else FORWARD
        motor_rampa.spin(direction, abs(value), PERCENT)

def aplicar_rampa_auto() -> None:
    """Modo automático de la rampa (370 RPM fijos)."""
    motor_rampa.set_velocity(370, RPM)
    motor_rampa.spin(FORWARD)

def toggle_rampa_mode() -> None:
    """Alterna entre modo rampa AUTO/MANUAL con botón B."""
    global modo_rampa_auto, prev_ButtonB
    if controller.buttonB.pressing() and not prev_ButtonB:
        modo_rampa_auto = not modo_rampa_auto
    prev_ButtonB = controller.buttonB.pressing()

def control_garra_gradual() -> None:
    """Control gradual de la garra con L1/R1."""
    if controller.buttonL1.pressing():
        motor_garra_open_close.spin(FORWARD, 60, PERCENT)
    elif controller.buttonR1.pressing():
        motor_garra_open_close.spin(REVERSE, 60, PERCENT)
    else:
        motor_garra_open_close.stop(HOLD)

def control_pinza_gradual() -> None:
    """Control gradual de la pinza con L2/R2."""
    if controller.buttonL2.pressing():
        motor_pinza_open_close.spin(FORWARD, 100, PERCENT)
    elif controller.buttonR2.pressing():
        motor_pinza_open_close.spin(REVERSE, 100, PERCENT)
    else:
        motor_pinza_open_close.stop(HOLD)

def girar_cepillo() -> None:
    """Toggle ON/OFF del cepillo con botón A."""
    global cepillo_on, prev_ButtonA
    if controller.buttonA.pressing() and not prev_ButtonA:
        cepillo_on = not cepillo_on
        if cepillo_on:
            motor_cepillo.spin(REVERSE, 100, PERCENT)
        else:
            motor_cepillo.stop()
    prev_ButtonA = controller.buttonA.pressing()

# ================================================================
# Bucle principal (Teleoperado)
# ================================================================
def main() -> None:
    """
    Bucle teleoperado:
      - Controla movimiento (arcade).
      - Controla rampa (manual/automático).
      - Alterna y aplica el modo rampa.
      - Actualiza cepillo, pinza y garra.
      - Espera 20 ms para no saturar CPU.
    """
    while True:
        # Movimiento base
        control_drive()

        # Actuadores
        girar_cepillo()
        control_pinza_gradual()
        control_garra_gradual()

        # Rampa (modo automático/manual)
        toggle_rampa_mode()
        if modo_rampa_auto:
            aplicar_rampa_auto()
        else:
            control_rampa()

        wait(20, MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()