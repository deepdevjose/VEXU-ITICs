# =================================================================
# VEXcode – Configuración y Teleoperado (Chico – Modo manual v2.0)
# -----------------------------------------------------------------
# Autor: @deepdevjose (refactor asistido)
# =================================================================
#
# NOTAS DE DISEÑO Y DECISIONES:
# --------------------------------
# - Direction Change Gate (cannon/way): Fuerza rampa a 0 antes de invertir
#   dirección para proteger mecánica. Durante tap-tap rápido verás pausas.
#
# - Override Cooldown (80ms): Bloquea edge-trigger de toggles A/B tras
#   soltar R1/L1 para evitar cambios accidentales. Brushes mantienen estado.
#
# - Slew Rate Simétrico: Misma velocidad accel/decel. Mejora futura:
#   step_accel vs step_decel diferenciados (frenado más rápido).
#
# - Semántica Motores: Brushes invertidos en constructor para que
#   FORWARD=recolectar, REVERSE=expulsar (100% semántico sin excepciones).
#
# - Mutual Exclusion: D-pad Up/Down y toggles A/B tienen protección
#   contra estados contradictorios.
#
# =================================================================

from vex import *

# ------------------------------------------------
# Inicialización del cerebro y controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# CONFIGURACIÓN DE PUERTOS
# ------------------------------------------------
# Tren motriz (verde 18:1)
DRIVE_LEFT_PORT   = Ports.PORT11
DRIVE_RIGHT_PORT  = Ports.PORT12

# Cepillos (verde 18:1)
BRUSH_FRONT_PORT  = Ports.PORT13
BRUSH_BOTTOM_PORT = Ports.PORT14

# Cañón (azul 6:1)
CANNON_PORT = Ports.PORT20
WAY_PORT = Ports.PORT15

# ------------------------------------------------
# PARÁMETROS DE TUNING (ajustar en campo)
# ------------------------------------------------
# Loop timing
LOOP_TIME_MS = 20

# Deadzone por eje
DEADZONE_FWD = 5
DEADZONE_TURN = 8

# Curva exponencial (0.0=lineal, 0.5=balanceado, 1.0=cúbico)
EXPO_FWD = 0.5
EXPO_TURN = 0.4

# Slew rate (% cambio por ciclo de 20ms)
SLEW_DRIVE = 8      # ~250ms para 0→100%
SLEW_BRUSH = 25     # Más rápido para brushes
SLEW_CANNON = 25
SLEW_WAY = 25       # Independiente para tuning

# Modo de frenado drivetrain
DRIVE_BRAKE_MODE = BrakeType.COAST

# Cooldown al soltar R1/L1 (ms sin aplicar toggles)
OVERRIDE_COOLDOWN_MS = 80  # Reducido para evitar "lag" perceptible

# ------------------------------------------------
# Instancias de motores
# ------------------------------------------------
# Drivetrain: reversed en constructor según montaje físico
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_18_1, False)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_18_1, True)

# Brushes: invertidos para semántica pura (FORWARD=recolectar, REVERSE=expulsar)
# Sin excepciones ni lógica invertida en código
brush_front  = Motor(BRUSH_FRONT_PORT,  GearSetting.RATIO_18_1, True)
brush_bottom = Motor(BRUSH_BOTTOM_PORT, GearSetting.RATIO_18_1, True)

# Cannon/WAY: ajustar reversed para que FORWARD=disparar, REVERSE=unjam
# Si el comportamiento no coincide, invertir aquí en vez de en el código
cannon = Motor(CANNON_PORT, GearSetting.RATIO_6_1, True)
way = Motor(WAY_PORT, GearSetting.RATIO_6_1, False)

# Pistones neumáticos
tumbaburros = DigitalOut(brain.three_wire_port.g)
ramp_piston = DigitalOut(brain.three_wire_port.h)

# ------------------------------------------------
# Configuración de motores
# ------------------------------------------------
# Torque máximo (100% = sin límite artificial)
motor_left.set_max_torque(100, PERCENT)
motor_right.set_max_torque(100, PERCENT)
brush_front.set_max_torque(100, PERCENT)
brush_bottom.set_max_torque(100, PERCENT)
cannon.set_max_torque(100, PERCENT)
way.set_max_torque(100, PERCENT)

# Modo de frenado
motor_left.set_stopping(DRIVE_BRAKE_MODE)
motor_right.set_stopping(DRIVE_BRAKE_MODE)
brush_front.set_stopping(BrakeType.BRAKE)
brush_bottom.set_stopping(BrakeType.BRAKE)
cannon.set_stopping(BrakeType.BRAKE)
way.set_stopping(BrakeType.BRAKE)

motor_left.set_velocity(100, PERCENT)
motor_right.set_velocity(100, PERCENT)

# ------------------------------------------------
# Constantes de estado (evita strings frágiles)
# ------------------------------------------------
BRUSH_OFF = 0
BRUSH_COLLECT = 1  # Intake/recolectar = FORWARD (semántico puro)
BRUSH_EJECT = 2    # Expulsar = REVERSE (semántico puro)

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
# Pistones
tumbaburros_extended = False
ramp_extended = False

# Toggles
brush_state = BRUSH_OFF
prev = {"R1": False, "L1": False, "A": False, "B": False, "Y": False, "Up": False, "Down": False}

# Slew state (valores actuales tras rampa)
slew_drive = {"L": 0, "R": 0}
slew_brush_pct = 0
slew_cannon_pct = 0
slew_way_pct = 0

# Cache de comandos aplicados (anti-spam)
last_drive_cmd = {"L": 0, "R": 0}
last_brush_cmd = {"pct": 0, "dir": "STOP"}
last_cannon_cmd = {"pct": 0, "dir": "STOP"}
last_way_cmd = {"pct": 0, "dir": "STOP"}

# Direction change gate (para cannon/way)
cannon_last_dir = "STOP"
way_last_dir = "STOP"

# Override R1/L1
override_cooldown_until = 0

# Telemetría
last_telemetry_ms = 0

# ------------------------------------------------
# Utilidades
# ------------------------------------------------
def now_ms() -> int:
    """Tiempo actual en milisegundos."""
    return brain.timer.time(MSEC)

def clamp(v: int, lo: int = -100, hi: int = 100) -> int:
    """Limita valor entre lo y hi."""
    return max(lo, min(hi, v))

def deadband(v: int, db: int) -> int:
    """Deadzone: retorna 0 si |v| < db."""
    return 0 if abs(v) < db else v

def expo(v: int, k: float) -> int:
    """Curva exponencial: y = (1-k)*x + k*x³
    Mejora precisión en zona media sin perder extremos.
    k=0 es lineal, k=1 es cúbico puro.
    """
    if v == 0:
        return 0
    x = max(-100, min(100, v)) / 100.0
    y = (1.0 - k) * x + k * (x * x * x)
    return int(round(y * 100))

def slew_step(current: int, target: int, step: int) -> int:
    """Rampa de aceleración: incrementa/decrementa 'step' hacia target.
    
    Nota: step es simétrico (misma velocidad para acelerar y frenar).
    Si quieres frenar más rápido que acelerar, necesitarías dos parámetros:
    step_accel y step_decel. Para la mayoría de casos, simétrico es suficiente.
    Soporta targets negativos correctamente.
    """
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return current

# ================================================================
# CAPA 1: Compute Setpoints (lógica de control)
# ================================================================
def compute_drive_setpoints() -> tuple:
    """Calcula setpoints de drivetrain con expo, deadzone y mezcla arcade.
    Retorna: (left_pct, right_pct)
    """
    fwd = deadband(controller.axis3.position(), DEADZONE_FWD)
    turn = deadband(controller.axis4.position(), DEADZONE_TURN)

    fwd = expo(fwd, EXPO_FWD)
    turn = expo(turn, EXPO_TURN)

    left = clamp(fwd + turn)
    right = clamp(fwd - turn)
    return left, right

def update_toggles():
    """Actualiza estados de toggles (A, B, Y, Up, Down).
    Bloquea A/B durante cooldown para que override sea modo exclusivo.
    """
    global brush_state, tumbaburros_extended, ramp_extended

    # Bloquear A/B durante cooldown (override tiene prioridad)
    if now_ms() < override_cooldown_until:
        prev["A"] = controller.buttonA.pressing()
        prev["B"] = controller.buttonB.pressing()
        # Y, Up, Down se procesan normalmente (no interfieren con override)
    else:
        # Procesar toggles A/B normalmente
        a = controller.buttonA.pressing()
        if a and not prev["A"]:
            brush_state = BRUSH_OFF if brush_state == BRUSH_COLLECT else BRUSH_COLLECT
        prev["A"] = a

        b = controller.buttonB.pressing()
        if b and not prev["B"]:
            brush_state = BRUSH_OFF if brush_state == BRUSH_EJECT else BRUSH_EJECT
        prev["B"] = b

    y = controller.buttonY.pressing()
    if y and not prev["Y"]:
        tumbaburros_extended = not tumbaburros_extended
    prev["Y"] = y

    up = controller.buttonUp.pressing()
    down = controller.buttonDown.pressing()
    
    # Mutual exclusion: ignorar si ambos presionados
    if up and down:
        pass  # Conflicto: no cambiar estado
    elif up and not prev["Up"]:
        ramp_extended = True
    elif down and not prev["Down"]:
        ramp_extended = False
    
    prev["Up"] = up
    prev["Down"] = down

def compute_mechanism_setpoints() -> tuple:
    """Calcula setpoints de cannon/way/brushes con prioridad override > toggles.
    Retorna: (brush_cmd, cannon_cmd, way_cmd)
    donde cmd = (pct, dir) con dir in ["FORWARD", "REVERSE", "STOP"]
    """
    global override_cooldown_until

    r1 = controller.buttonR1.pressing()
    l1 = controller.buttonL1.pressing()

    # Prioridad 1: Override R1/L1 (control directo)
    if r1:
        override_cooldown_until = now_ms() + OVERRIDE_COOLDOWN_MS
        return (100, "REVERSE"), (100, "REVERSE"), (100, "REVERSE")

    if l1:
        override_cooldown_until = now_ms() + OVERRIDE_COOLDOWN_MS
        return (100, "FORWARD"), (100, "FORWARD"), (100, "FORWARD")

    # Cooldown: cannon/way STOP, brushes mantienen toggle
    if now_ms() < override_cooldown_until:
        brush_cmd = get_toggle_brush_cmd()
        return brush_cmd, (0, "STOP"), (0, "STOP")

    # Prioridad 2: Toggles A/B (solo brushes, cannon/way detenidos)
    brush_cmd = get_toggle_brush_cmd()
    return brush_cmd, (0, "STOP"), (0, "STOP")

def get_toggle_brush_cmd() -> tuple:
    """Retorna comando de brush según estado del toggle.
    Semántica pura: COLLECT=FORWARD, EJECT=REVERSE (motores ya invertidos).
    """
    if brush_state == BRUSH_COLLECT:
        return (100, "FORWARD")   # Recolectar
    if brush_state == BRUSH_EJECT:
        return (100, "REVERSE")   # Expulsar
    return (0, "STOP")

# ================================================================
# CAPA 2: Apply Actuators (físico con cache, slew, anti-spam)
# ================================================================
def apply_drive(left_target: int, right_target: int):
    """Aplica setpoints de drivetrain con slew rate y anti-spam.
    Usa abs() + dirección explícita para evitar ambigüedad con valores negativos.
    """
    # Aplicar rampa
    slew_drive["L"] = slew_step(slew_drive["L"], left_target, SLEW_DRIVE)
    slew_drive["R"] = slew_step(slew_drive["R"], right_target, SLEW_DRIVE)

    # Anti-spam: solo enviar si cambió
    if slew_drive["L"] != last_drive_cmd["L"]:
        val = slew_drive["L"]
        if val == 0:
            motor_left.stop()
        elif val > 0:
            motor_left.spin(FORWARD, val, PERCENT)
        else:
            motor_left.spin(REVERSE, abs(val), PERCENT)
        last_drive_cmd["L"] = val

    if slew_drive["R"] != last_drive_cmd["R"]:
        val = slew_drive["R"]
        if val == 0:
            motor_right.stop()
        elif val > 0:
            motor_right.spin(FORWARD, val, PERCENT)
        else:
            motor_right.spin(REVERSE, abs(val), PERCENT)
        last_drive_cmd["R"] = val

def apply_brushes(cmd: tuple):
    """Aplica comando de brushes con slew y anti-spam."""
    global slew_brush_pct

    pct, direction = cmd

    # Slew rate hacia magnitud deseada
    target_mag = 0 if direction == "STOP" else pct
    slew_brush_pct = slew_step(slew_brush_pct, target_mag, SLEW_BRUSH)

    # Determinar dirección y magnitud finales
    if slew_brush_pct == 0:
        final_dir = "STOP"
        final_pct = 0
    else:
        final_dir = direction
        final_pct = slew_brush_pct

    # Anti-spam
    if final_pct == last_brush_cmd["pct"] and final_dir == last_brush_cmd["dir"]:
        return

    # Aplicar a motores
    if final_dir == "STOP":
        brush_front.stop()
        brush_bottom.stop()
    elif final_dir == "FORWARD":
        brush_front.spin(FORWARD, final_pct, PERCENT)
        brush_bottom.spin(FORWARD, final_pct, PERCENT)
    else:
        brush_front.spin(REVERSE, final_pct, PERCENT)
        brush_bottom.spin(REVERSE, final_pct, PERCENT)

    last_brush_cmd["pct"] = final_pct
    last_brush_cmd["dir"] = final_dir

def apply_cannon(cmd: tuple):
    """Aplica comando de cañón con slew y direction change gate.
    Ver NOTAS DE DISEÑO al inicio del archivo para detalles.
    """
    global slew_cannon_pct, cannon_last_dir

    pct, desired_dir = cmd

    # Direction change gate: si cambio de dirección con motor en movimiento
    if desired_dir != cannon_last_dir and desired_dir != "STOP" and cannon_last_dir != "STOP":
        if slew_cannon_pct > 0:
            # Forzar rampa a 0 antes de permitir nuevo sentido
            desired_dir = "STOP"

    # Slew rate hacia magnitud deseada
    target = 0 if desired_dir == "STOP" else pct
    slew_cannon_pct = slew_step(slew_cannon_pct, target, SLEW_CANNON)

    # Determinar dirección final
    if slew_cannon_pct == 0:
        final_dir = "STOP"
        cannon_last_dir = "STOP"  # Reset para permitir nueva dirección
    else:
        final_dir = desired_dir
        cannon_last_dir = desired_dir

    # Anti-spam
    if slew_cannon_pct == last_cannon_cmd["pct"] and final_dir == last_cannon_cmd["dir"]:
        return

    # Aplicar a motor
    if final_dir == "STOP":
        cannon.stop()
    elif final_dir == "FORWARD":
        cannon.spin(FORWARD, slew_cannon_pct, PERCENT)
    else:
        cannon.spin(REVERSE, slew_cannon_pct, PERCENT)

    last_cannon_cmd["pct"] = slew_cannon_pct
    last_cannon_cmd["dir"] = final_dir

def apply_way(cmd: tuple):
    """Aplica comando de motor WAY con slew y direction change gate.
    Ver NOTAS DE DISEÑO al inicio del archivo para detalles.
    """
    global slew_way_pct, way_last_dir

    pct, desired_dir = cmd

    # Direction change gate: si cambio de dirección con motor en movimiento
    if desired_dir != way_last_dir and desired_dir != "STOP" and way_last_dir != "STOP":
        if slew_way_pct > 0:
            # Forzar rampa a 0 antes de permitir nuevo sentido
            desired_dir = "STOP"

    # Slew rate
    target = 0 if desired_dir == "STOP" else pct
    slew_way_pct = slew_step(slew_way_pct, target, SLEW_WAY)

    # Determinar dirección final
    if slew_way_pct == 0:
        final_dir = "STOP"
        way_last_dir = "STOP"  # Reset para permitir nueva dirección
    else:
        final_dir = desired_dir
        way_last_dir = desired_dir

    # Anti-spam
    if slew_way_pct == last_way_cmd["pct"] and final_dir == last_way_cmd["dir"]:
        return

    # Aplicar a motor
    if final_dir == "STOP":
        way.stop()
    elif final_dir == "FORWARD":
        way.spin(FORWARD, slew_way_pct, PERCENT)
    else:
        way.spin(REVERSE, slew_way_pct, PERCENT)

    last_way_cmd["pct"] = slew_way_pct
    last_way_cmd["dir"] = final_dir

def apply_pistons():
    """Aplica estados de pistones neumáticos."""
    ramp_piston.set(ramp_extended)
    tumbaburros.set(tumbaburros_extended)

# ================================================================
# Inicialización
# ================================================================
def init_positions():
    """Posiciones iniciales seguras."""
    cannon.reset_position()
    cannon.stop()
    way.reset_position()
    way.stop()
    ramp_piston.set(False)
    tumbaburros.set(False)

# ================================================================
# Bucle principal
# ================================================================
def main():
    """Loop principal de teleoperado."""
    global last_telemetry_ms

    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Chico Robot v2.0")

    init_positions()
    last_telemetry_ms = now_ms()

    while True:
        cycle_start = now_ms()

        # 1) Leer inputs y compute setpoints
        update_toggles()
        left_sp, right_sp = compute_drive_setpoints()
        brush_cmd, cannon_cmd, way_cmd = compute_mechanism_setpoints()

        # 2) Apply a motores físicos
        apply_drive(left_sp, right_sp)
        apply_brushes(brush_cmd)
        apply_cannon(cannon_cmd)
        apply_way(way_cmd)
        apply_pistons()

        # 3) Telemetría estable (cada 100ms, sin jitter)
        t = now_ms()
        if (t - last_telemetry_ms) >= 100:
            last_telemetry_ms = t
            
            brain.screen.set_cursor(2, 1)
            brain.screen.print("Ramp:{} Tumb:{} Brush:{}  ".format(
                "UP" if ramp_extended else "DN",
                "UP" if tumbaburros_extended else "DN",
                ["OFF", "COL", "EJT"][brush_state]
            ))
            
            brain.screen.set_cursor(3, 1)
            brain.screen.print("Br:{}{} Cn:{}{} Wy:{}{}  ".format(
                last_brush_cmd["dir"][0],
                last_brush_cmd["pct"],
                last_cannon_cmd["dir"][0],
                last_cannon_cmd["pct"],
                last_way_cmd["dir"][0],
                last_way_cmd["pct"]
            ))

        # 4) Loop timing adaptativo
        elapsed = now_ms() - cycle_start
        wait(max(1, LOOP_TIME_MS - elapsed), MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()

