# ================================================================
# VEXcode – Configuración y Teleoperado (PushBack – Modo manual)
# ---------------------------------------------------------------
# Descripción:
#   Control arcade de tren motriz 2× motores + rampa 3 niveles,
#   cañón de un solo carril, cepillos sincronizados, pitillo (toggle).
#
#   • Conducción tipo arcade:
#       - Axis3: avance/retroceso
#       - Axis4: giro izquierda/derecha
#
#   • Rampa (puertos 11 izq, 12 der [invertido], rojo 36:1):
#       - ButtonUp    -> ALTO  (50°)
#       - ButtonLeft/Right -> MEDIO (35°)
#       - ButtonDown  -> BAJO  (0°)
#       - Transición suave; HOLD en cada nivel; arranca en BAJO.
#
#   • Cañón (puerto 19 azul 6:1, referencia en 0°):
#       - R1: mientras presionado -> SPIN FORWARD @100%
#       - L1: mientras presionado -> SPIN REVERSE @100%
#
#   • Cepillos sincronizados (puertos 16 y 20, verde 18:1):
#       - ButtonA: ambos en REVERSE @100%
#       - ButtonB: ambos en FORWARD @100%
#       - Ninguno: detenidos
#
#   • Pitillo (verde 18:1, por defecto ARRIBA=0°):
#       - ButtonY: alterna ARRIBA(0°) <-> ABAJO(135°); HOLD en ambos.
#
# Notas:
#   - Ajusta inversión del motor derecho del tren si es necesario.
#   - Cambia el puerto del pitillo si usas otro (por defecto 18).
#
# Autor: basado en la estructura del equipo por @deepdevjose
# ================================================================

from vex import *

# ------------------------------------------------
# Inicialización del cerebro y controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# CONFIGURACIÓN DE PUERTOS Y RATIOS
# ------------------------------------------------
# Tren motriz (verde 18:1)
DRIVE_LEFT_PORT   = Ports.PORT11
DRIVE_RIGHT_PORT  = Ports.PORT12
DRIVE_RIGHT_REVERSED = False

# Cepillos (verde 18:1)
BRUSH_FRONT_PORT  = Ports.PORT13
BRUSH_BOTTOM_PORT = Ports.PORT14

# Cañón (azul 6:1)
CANNON_PORT = Ports.PORT20
WAY = Ports.PORT15


# Rampa (rojo 36:1) – izquierda +° sube, derecha -° sube
RAMP_LEFT_PORT  = Ports.PORT16
RAMP_RIGHT_PORT = Ports.PORT17

# Pitillo (verde 18:1)
PITILLO_PORT = Ports.PORT18  

# ------------------------------------------------
# Instancias de motores y actuadores
# ------------------------------------------------
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_18_1, True)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_18_1, DRIVE_RIGHT_REVERSED)

brush_front  = Motor(BRUSH_FRONT_PORT,  GearSetting.RATIO_18_1, False)
brush_bottom = Motor(BRUSH_BOTTOM_PORT, GearSetting.RATIO_18_1, False)

cannon = Motor(CANNON_PORT, GearSetting.RATIO_6_1, False)
# Motor auxiliar sincronizado con el cañón (WAY). Asumo relación similar 6:1
way = Motor(WAY, GearSetting.RATIO_6_1, True)

ramp_left  = Motor(RAMP_LEFT_PORT,  GearSetting.RATIO_36_1, False)  # +° sube
ramp_right = Motor(RAMP_RIGHT_PORT, GearSetting.RATIO_36_1, False)   # invertido: +° baja

pitillo = Motor(PITILLO_PORT, GearSetting.RATIO_18_1, False)

# Modos de frenado
for m in (ramp_left, ramp_right, pitillo):
    m.set_stopping(BrakeType.HOLD)
for m in (motor_left, motor_right, brush_front, brush_bottom, cannon):
    m.set_stopping(BrakeType.COAST)
# Alineamos modo de frenado de WAY con el cañón
way.set_stopping(BrakeType.COAST)

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
DEADZONE = 5

RAMP_LEVELS = {"BAJO": 0, "MEDIO": 50, "ALTO": 50}
ramp_target = RAMP_LEVELS["BAJO"]

pitillo_is_down = False
brushes_state = "OFF"  # "OFF", "REVERSE", "FORWARD"
   
prev = {"R1": False, "L1": False, "Y": False, "A": False, "B": False}

# ------------------------------------------------
# Utilidades
# ------------------------------------------------
def deadband(v: int, db: int = DEADZONE) -> int:
    return 0 if abs(v) < db else v

def clamp(v: int, lo: int = -100, hi: int = 100) -> int:
    return max(lo, min(hi, v))

def at_target(m: Motor, deg: float, tol: float = 1.0) -> bool:
    return abs(m.position(DEGREES) - deg) <= tol

# ================================================================
# Funciones de Movimiento (Tren motriz)
# ================================================================
def control_drive_arcade() -> None:
    """
    Arcade:
      - Axis3 = avance/retroceso
      - Axis4 = giro
    """
    forward = deadband(controller.axis3.position())
    turn    = deadband(controller.axis1.position())

    left_pct  = clamp(forward + turn)
    right_pct = clamp(forward - turn)

    motor_left.spin(REVERSE, left_pct, PERCENT)
    motor_right.spin(REVERSE, right_pct, PERCENT)

# ================================================================
# Rampa (3 niveles con transición suave y parada en estado)
# ================================================================
def control_rampa_niveles() -> None:
    global ramp_target
    if controller.buttonUp.pressing():
        ramp_target = RAMP_LEVELS["ALTO"]
    elif controller.buttonLeft.pressing() or controller.buttonRight.pressing():
        ramp_target = RAMP_LEVELS["MEDIO"]
    elif controller.buttonDown.pressing():
        ramp_target = RAMP_LEVELS["BAJO"]

    # Mover no bloqueante hacia el objetivo con velocidad más suave (30%)
    if not (at_target(ramp_left, ramp_target) and at_target(ramp_right, -ramp_target)):
        ramp_left.spin_to_position(ramp_target, DEGREES, 30, PERCENT, False)
        ramp_right.spin_to_position(-ramp_target, DEGREES, 30, PERCENT, False)
    else:
        ramp_left.stop()
        ramp_right.stop()

# ================================================================
# Cañón (doble carril con retorno a 0°)
# ================================================================
def control_canon() -> None:
    # Nuevo comportamiento: mientras R1 esté presionado -> FORWARD;
    # mientras L1 esté presionado -> REVERSE. Si ninguno, detener.
    r1 = controller.buttonR1.pressing()
    l1 = controller.buttonL1.pressing()

    # Sincronizar también el motor WAY con el cañón.
    # Mapear: R1 -> FORWARD, L1 -> REVERSE (mientras se presionen).
    if l1 and not r1:
        cannon.set_velocity(100, PERCENT)
        way.set_velocity(100, PERCENT)
        cannon.spin(FORWARD)
        way.spin(FORWARD)
        # Activar cepillos en el mismo sentido mientras dispara el cañón
        brush_front.spin(FORWARD, 100, PERCENT)
        brush_bottom.spin(FORWARD, 100, PERCENT)
    elif r1 and not l1:
        cannon.set_velocity(100, PERCENT)
        way.set_velocity(100, PERCENT)
        cannon.spin(REVERSE)
        way.spin(REVERSE)
        # Activar cepillos en el mismo sentido (REVERSE) mientras dispara
        brush_front.spin(REVERSE, 100, PERCENT)
        brush_bottom.spin(REVERSE, 100, PERCENT)
    else:
        # Si presionan ambos o ninguno, detener ambos motores para evitar
        # movimientos conflictivos.
        cannon.stop()
        way.stop()

    prev["R1"] = r1
    prev["L1"] = l1

# ================================================================
# Cepillos sincronizados (toggle)
# ================================================================
def control_cepillos() -> None:
    global brushes_state
    

    # Invertimos la asignación según petición del usuario:
    # ButtonA -> toggle FORWARD (intake)
    a = controller.buttonA.pressing()
    if a and not prev["A"]:
        if brushes_state == "FORWARD":
            brushes_state = "OFF"
        else:
            brushes_state = "FORWARD"
    prev["A"] = a

    # ButtonB -> toggle REVERSE (expulse)
    b = controller.buttonB.pressing()
    if b and not prev["B"]:
        if brushes_state == "REVERSE":
            brushes_state = "OFF"
        else:
            brushes_state = "REVERSE"
    prev["B"] = b

    # Si el cañón está disparando (R1 o L1), no sobreescribir el estado
    # de los cepillos aquí: el cañón controla los cepillos mientras dispara.
    if controller.buttonR1.pressing() or controller.buttonL1.pressing():
        return

    # Aplicar estado: hacer que los estados correspondan a las direcciones
    if brushes_state == "FORWARD":
        brush_front.spin(REVERSE, 100, PERCENT)
        brush_bottom.spin(REVERSE, 100, PERCENT)
    elif brushes_state == "REVERSE":
        brush_front.spin(FORWARD, 100, PERCENT)
        brush_bottom.spin(FORWARD, 100, PERCENT)
    else:
        brush_front.stop()
        brush_bottom.stop()

# ================================================================
# Pitillo (toggle con Y, manual con L2/R2)
# ================================================================
def control_pitillo_toggle() -> None:
    global pitillo_is_down
    
    # Control manual con L2 (bajar) y R2 (subir)
    if controller.buttonL2.pressing():
        pitillo.spin(FORWARD, 50, PERCENT)  # bajar (hacia 135°)
    elif controller.buttonR2.pressing():
        pitillo.spin(REVERSE, 50, PERCENT)  # subir (hacia 0°)
    else:
        # Toggle automático con Y solo si no hay control manual
        y = controller.buttonY.pressing()
        if y and not prev["Y"]:
            pitillo_is_down = not pitillo_is_down
            target = 165 if pitillo_is_down else 0
            pitillo.spin_to_position(target, DEGREES, 130, PERCENT, False)
        # Detener el pitillo cuando no hay comandos
        if not y or (y and prev["Y"]):
            pitillo.stop()
        prev["Y"] = y

# ================================================================
# Inicialización de posiciones y estados
# ================================================================
def init_positions() -> None:
    # Rampa a BAJO=0°, HOLD
    ramp_left.reset_position()
    ramp_right.reset_position()
    ramp_left.spin_to_position(0, DEGREES, 60, PERCENT, False)
    ramp_right.spin_to_position(0, DEGREES, 60, PERCENT, False)

    # Cañón a 0°
    cannon.reset_position()
    cannon.stop()

    # Pitillo ARRIBA=0°, HOLD
    pitillo.reset_position()
    pitillo.spin_to_position(0, DEGREES, 60, PERCENT, False)

# ================================================================
# Bucle principal (Teleoperado)
# ================================================================
def main() -> None:
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("PushBack listo")

    init_positions()

    while True:
        control_drive_arcade()
        control_rampa_niveles()
        control_canon()
        control_cepillos()
        control_pitillo_toggle()

        # Telemetría mínima
        brain.screen.set_cursor(2, 1)
        brain.screen.print("Rampa:{:>3}  Pitillo:{}".format(
            ramp_target, "ABJ" if pitillo_is_down else "ARR"))
        wait(20, MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()
