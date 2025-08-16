# ================================================================
# VEXcode – Configuración y Teleoperado (VEX IQ con 4 motores)
# ---------------------------------------------------------------
# Descripción:
#   Control de un robot VEX IQ con tren motriz de 4 motores
#   y un motor adicional para el cepillo.
#
#   • Conducción tipo arcade:
#       - AxisA: avance/retroceso
#       - AxisB: giro izquierda/derecha
#   • Cepillo:
#       - ButtonFDown: gira hacia adelante
#       - ButtonFUp:   gira hacia atrás
#
# Notas:
#   - Usa DEADZONE para evitar ruido del joystick.
#   - La semilla aleatoria se inicializa con sensores (voltaje, corriente, tiempo).
#
# Autor: @deepdevjose - github.com/deepdevjose
# ================================================================

#region VEX IQ Robot Configuration
from vex import *

# ------------------------------------------------
# Inicialización del cerebro y el controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# Motores del tren motriz
# ------------------------------------------------
motor_back_left   = Motor(Ports.PORT12, False)  # Trasera izquierda
motor_back_right  = Motor(Ports.PORT6, True)    # Trasera derecha
motor_front_left  = Motor(Ports.PORT7, False)   # Delantera izquierda
motor_front_right = Motor(Ports.PORT1, True)    # Delantera derecha

# ------------------------------------------------
# Motor adicional
# ------------------------------------------------
motor_cepillo = Motor(Ports.PORT8, False)

# ------------------------------------------------
# Constantes
# ------------------------------------------------
DEADZONE = 10  # Ignorar ruido pequeño en joystick

# ================================================================
# Funciones de Movimiento (Tren motriz)
# ================================================================
def mover_adelante(velocidad: int) -> None:
    """Avanza hacia adelante a velocidad (%)."""
    motor_back_left.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def mover_atras(velocidad: int) -> None:
    """Retrocede a velocidad (%)."""
    motor_back_left.spin(REVERSE, velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def girar_izquierda(velocidad: int) -> None:
    """Giro en su lugar hacia la izquierda."""
    motor_back_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def girar_derecha(velocidad: int) -> None:
    """Giro en su lugar hacia la derecha."""
    motor_back_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def detener() -> None:
    """Detiene todos los motores del tren motriz."""
    motor_back_left.stop()
    motor_back_right.stop()
    motor_front_left.stop()
    motor_front_right.stop()

# ================================================================
# Control Arcade con AxisA (avance/retro) y AxisB (giro)
# ================================================================
def control_drive() -> None:
    """
    Conducción arcade:
      - AxisA: avance (+) / retroceso (–)
      - AxisB: giro derecha (+) / izquierda (–)
    """
    forward = controller.axisA.position()
    turn    = controller.axisB.position()

    # Aplicar zona muerta
    if abs(forward) < DEADZONE: forward = 0
    if abs(turn) < DEADZONE: turn = 0

    # Mezcla diferencial
    left_speed  = forward + turn
    right_speed = forward - turn

    # Asignar a motores
    motor_back_left.spin(FORWARD, left_speed, PERCENT)
    motor_front_left.spin(FORWARD, left_speed, PERCENT)
    motor_back_right.spin(FORWARD, right_speed, PERCENT)
    motor_front_right.spin(FORWARD, right_speed, PERCENT)

# ================================================================
# Control de Cepillo
# ================================================================
def controlar_cepillo() -> None:
    """
    Control del motor de cepillo:
      - ButtonFDown: gira en FORWARD al 100%
      - ButtonFUp:   gira en REVERSE al 100%
      - Ninguno:     se detiene
    """
    if controller.buttonFDown.pressing():
        motor_cepillo.spin(FORWARD, 100, PERCENT)
    elif controller.buttonFUp.pressing():
        motor_cepillo.spin(REVERSE, 100, PERCENT)
    else:
        motor_cepillo.stop()

# ================================================================
# Bucle Principal
# ================================================================
def main() -> None:
    """
    Bucle teleoperado:
      - Control arcade (avance + giro).
      - Control de cepillo.
      - Delay de 20 ms para estabilidad.
    """
    while True:
        control_drive()
        controlar_cepillo()
        wait(20, MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()
