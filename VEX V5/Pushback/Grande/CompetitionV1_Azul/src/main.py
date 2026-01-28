# =================================================================
# VEXcode – Competencia Oficial (Grande – v3.0)
# -----------------------------------------------------------------
#
# Autor: @deepdevjose
# =================================================================

from vex import *
import time

# Import typing si está disponible
try:
    from typing import Optional
except:
    Optional = None

# ------------------------------------------------
# Inicialización del cerebro y controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# CONFIGURACIÓN DE PUERTOS Y RATIOS
# ------------------------------------------------
# Tren motriz (rojos 36:1)
DRIVE_LEFT_PORT   = Ports.PORT3
DRIVE_RIGHT_PORT  = Ports.PORT4

# Intake (azul 6:1)
INTAKE_PORT = Ports.PORT20
INTAKE_SUP_PORT = Ports.PORT11

# Cañón (verde 18:1)
CANNON_PORT = Ports.PORT16

# Sensor óptico
OPTICAL_SENSOR_PORT = Ports.PORT19

# ------------------------------------------------
# PARÁMETROS DE TUNING
# ------------------------------------------------
# Loop timing
LOOP_TIME_MS = 20

# Deadzone por eje
DEADZONE_FWD = 5
DEADZONE_TURN = 8

# Curva exponencial
EXPO_FWD = 0.5
EXPO_TURN = 0.4

# Slew rate asimétrico
SLEW_DRIVE_ACCEL = 8
SLEW_DRIVE_DECEL = 15
SLEW_INTAKE_ACCEL = 25
SLEW_INTAKE_DECEL = 40
SLEW_CANNON_ACCEL = 25
SLEW_CANNON_DECEL = 40

# Modo de frenado drivetrain
DRIVE_BRAKE_MODE = BrakeType.COAST

# Cooldown al soltar R1/L1
OVERRIDE_COOLDOWN_MS = 100

# Debounce para pistones
PISTON_DEBOUNCE_MS = 200

# Anti-atasco (stall detection)
ANTI_STALL_ENABLED = True
STALL_SPEED_RPM = 30
STALL_CMD_MIN_PCT = 70
STALL_DETECT_MS = 250
STALL_GRACE_PERIOD_MS = 150
STALL_PULSE_REVERSE_MS = 180
STALL_PULSE_FORWARD_MS = 250

# Derating térmico
DERATING_ENABLED = True
TEMP_WARN_C = 50.0
TEMP_SOFT_C = 55.0
TEMP_HARD_C = 60.0
DERATE_SOFT = 85
DERATE_HARD = 70

# Rangos de colores para sensor óptico (HUE)
COLOR_RED_MIN = 3
COLOR_RED_MAX = 17
COLOR_BLUE_MIN = 148
COLOR_BLUE_MAX = 215

# ------------------------------------------------
# Parámetros de odometría 2D
# ------------------------------------------------
WHEEL_DIAMETER_CM = 10.0
WHEEL_TRAVEL_CM = 33.5
WHEEL_DEGREES = 364.0
DEGREES_PER_CM = WHEEL_DEGREES / WHEEL_TRAVEL_CM

# ------------------------------------------------
# Instancias de motores
# ------------------------------------------------
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_36_1, False) 
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_36_1, True)

intake = Motor(INTAKE_PORT, GearSetting.RATIO_6_1, False)
intake_sup = Motor(INTAKE_SUP_PORT, GearSetting.RATIO_6_1, True)

cannon = Motor(CANNON_PORT, GearSetting.RATIO_18_1, False)

# Pistones neumáticos
piston_trasero = DigitalOut(brain.three_wire_port.a)
piston_descores = DigitalOut(brain.three_wire_port.b)

# Sensor óptico
optical_sensor = Optical(OPTICAL_SENSOR_PORT)

# ------------------------------------------------
# Configuración de motores
# ------------------------------------------------
motor_left.set_max_torque(100, PERCENT)
motor_right.set_max_torque(100, PERCENT)
intake.set_max_torque(100, PERCENT)
intake_sup.set_max_torque(100, PERCENT)
cannon.set_max_torque(100, PERCENT)

motor_left.set_stopping(DRIVE_BRAKE_MODE)
motor_right.set_stopping(DRIVE_BRAKE_MODE)
intake.set_stopping(BrakeType.BRAKE)
intake_sup.set_stopping(BrakeType.BRAKE)
cannon.set_stopping(BrakeType.BRAKE)

motor_left.set_velocity(100, PERCENT)
motor_right.set_velocity(100, PERCENT)

# ------------------------------------------------
# Constantes de estado
# ------------------------------------------------
INTAKE_OFF = 0
INTAKE_A_ON = 1
INTAKE_B_ON = 2

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
# Configuración permanente: EQUIPO ROJO
# No requiere selección - siempre rechaza pelotas azules
team_is_red = True  # FIJO: No cambiar

# Pistones
descore_open = False
trasero_open = False
last_piston_toggle = {"Y": 0, "X": 0}

# Toggles
intake_state = INTAKE_OFF
prev = {"R1": False, "L1": False, "A": False, "B": False, "Y": False, "X": False}

# Estado de dirección para rampa segura
cannon_dir_state = "STOP"

# Slew state
slew_drive = {"L": 0, "R": 0}
slew_intake_pct = 0
slew_cannon_pct = 0

# Cache de comandos aplicados
last_drive_cmd = {"L": 0, "R": 0}
last_intake_cmd = {"pct": 0, "dir": "STOP"}
last_cannon_cmd = {"pct": 0, "dir": "STOP"}

# Override R1/L1
override_cooldown_until = 0

# Anti-stall state machine
stall = {
    "phase": "IDLE",
    "since_ms": 0,
    "phase_until_ms": 0,
    "last_cmd_dir": "STOP",
}

# Telemetría
last_telemetry_ms = 0
last_temp_sample_ms = 0
sensor_failures = {
    "intake_temp": 0,
    "intake_sup_temp": 0,
    "cannon_temp": 0, 
    "intake_vel": 0
}

# Cache de temperaturas
temp_cache = {
    "intake": (0, "OK"), 
    "intake_sup": (0, "OK"),
    "cannon": (0, "OK")
}

# ================================================================
# FUNCIONES UTILITARIAS
# ================================================================
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
    """Curva exponencial: y = (1-k)*x + k*x³"""
    if v == 0:
        return 0
    x = max(-100, min(100, v)) / 100.0
    y = (1.0 - k) * x + k * (x * x * x)
    return int(round(y * 100))

def slew_step(current: int, target: int, step_accel: int, step_decel = None) -> int:
    """Slew asimétrico robusto."""
    if step_decel is None:
        step_decel = step_accel

    if current == target:
        return current

    # Si cambia de signo, primero ir hacia 0 con decel
    if current != 0 and target != 0 and (current > 0) != (target > 0):
        if current > 0:
            return max(current - step_decel, 0)
        else:
            return min(current + step_decel, 0)

    # Misma dirección: decidir por magnitud
    if abs(target) > abs(current):
        step = step_accel
    else:
        step = step_decel

    if current < target:
        return min(current + step, target)
    else:
        return max(current - step, target)

def temp_derate_pct(motor_name: str) -> int:
    """Retorna factor de reducción (%) según temperatura del motor."""
    if not DERATING_ENABLED:
        return 100
    
    temp, status = temp_cache.get(motor_name, (0, "ERR"))
    
    if status == "ERR":
        return 100
    if status == "HARD":
        return DERATE_HARD
    if status == "SOFT":
        return DERATE_SOFT
    if status == "WARN":
        return 95
    return 100

def get_temp_status(m: Motor) -> tuple:
    """Retorna (temperatura, estado)."""
    try:
        t = m.temperature()
        if t >= TEMP_HARD_C:
            return (t, "HARD")
        if t >= TEMP_SOFT_C:
            return (t, "SOFT")
        if t >= TEMP_WARN_C:
            return (t, "WARN")
        return (t, "OK")
    except:
        return (0, "ERR")

def sample_temperatures():
    """Sample de temperaturas cada ~50ms."""
    global temp_cache
    
    def classify_temp(t):
        if t >= TEMP_HARD_C:
            return "HARD"
        elif t >= TEMP_SOFT_C:
            return "SOFT"
        elif t >= TEMP_WARN_C:
            return "WARN"
        else:
            return "OK"
    
    # Intake principal
    try:
        t = intake.temperature()
        temp_cache["intake"] = (t, classify_temp(t))
    except:
        sensor_failures["intake_temp"] += 1
        temp_cache["intake"] = (0, "ERR")
    
    # Intake superior
    try:
        t = intake_sup.temperature()
        temp_cache["intake_sup"] = (t, classify_temp(t))
    except:
        sensor_failures["intake_sup_temp"] += 1
        temp_cache["intake_sup"] = (0, "ERR")
    
    # Cannon
    try:
        t = cannon.temperature()
        temp_cache["cannon"] = (t, classify_temp(t))
    except:
        sensor_failures["cannon_temp"] += 1
        temp_cache["cannon"] = (0, "ERR")

def get_worst_status(status1: str, status2: str) -> str:
    """Retorna el peor status térmico por severidad."""
    severity = {"ERR": 0, "HARD": 4, "SOFT": 3, "WARN": 2, "OK": 1}
    s1_sev = severity.get(status1, 0)
    s2_sev = severity.get(status2, 0)
    return status1 if s1_sev >= s2_sev else status2

# ================================================================
# FUNCIONES DE DETECCIÓN DE COLORES
# ================================================================
def is_red_detected() -> bool:
    """Verifica si el sensor detecta color rojo."""
    hue = optical_sensor.hue()
    return COLOR_RED_MIN <= hue <= COLOR_RED_MAX

def is_blue_detected() -> bool:
    """Verifica si el sensor detecta color azul."""
    hue = optical_sensor.hue()
    return COLOR_BLUE_MIN <= hue <= COLOR_BLUE_MAX

def is_object_near() -> bool:
    """Verifica si hay un objeto cerca."""
    return optical_sensor.is_near_object()

# NOTA: Función select_team() eliminada
# El robot está configurado permanentemente para EQUIPO ROJO

# ================================================================
# FUNCIONES DE MOVIMIENTO AUTÓNOMO
# ================================================================
def drive_distance_cm(distance_cm: float, velocity: int = 50) -> None:
    """Mueve el robot una distancia específica en centímetros."""
    degrees_to_turn = distance_cm * DEGREES_PER_CM
    
    motor_left.reset_position()
    motor_right.reset_position()
    
    direction = FORWARD if distance_cm > 0 else REVERSE
    degrees_abs = abs(degrees_to_turn)
    
    motor_left.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, False)
    motor_right.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, True)

def turn_right_degrees(degrees: float, velocity: int) -> None:
    """Gira el robot a la derecha."""
    duration = abs(degrees) / 100.0
    motor_left.spin(FORWARD, velocity, PERCENT)
    motor_right.spin(REVERSE, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_left_pivot_90(velocity: int = 50) -> None:
    """Gira 90 grados a la izquierda pivotando sobre la llanta izquierda."""
    pivot_distance_cm = 20.0
    degrees_to_turn = pivot_distance_cm * DEGREES_PER_CM
    
    motor_right.reset_position()
    motor_left.stop(BrakeType.BRAKE)
    motor_right.spin_for(FORWARD, degrees_to_turn, DEGREES, velocity, PERCENT, True)
    
    motor_right.stop(BrakeType.BRAKE)
    motor_left.reset_position()
    
    back_distance_cm = 15.5
    back_degrees = back_distance_cm * DEGREES_PER_CM
    motor_left.spin_for(REVERSE, back_degrees, DEGREES, velocity, PERCENT)
    
    motor_left.stop(BrakeType.BRAKE)
    motor_right.stop(BrakeType.BRAKE)

# ================================================================
# CAPA 1: COMPUTE SETPOINTS (TELEOPERADO)
# ================================================================
def compute_drive_setpoints() -> tuple:
    """Calcula setpoints de drivetrain."""
    fwd = deadband(controller.axis3.position(), DEADZONE_FWD)
    turn = deadband(controller.axis4.position(), DEADZONE_TURN)

    fwd = expo(fwd, EXPO_FWD)
    turn = expo(turn, EXPO_TURN)

    left = clamp(fwd + turn)
    right = clamp(fwd - turn)
    return left, right

def update_toggles():
    """Actualiza estados de toggles."""
    global intake_state, descore_open, trasero_open
    
    t = now_ms()

    a = controller.buttonA.pressing()
    if a and not prev["A"]:
        intake_state = INTAKE_OFF if intake_state == INTAKE_A_ON else INTAKE_A_ON
    prev["A"] = a

    b = controller.buttonB.pressing()
    if b and not prev["B"]:
        intake_state = INTAKE_OFF if intake_state == INTAKE_B_ON else INTAKE_B_ON
    prev["B"] = b

    y = controller.buttonY.pressing()
    if y and not prev["Y"]:
        if (t - last_piston_toggle["Y"]) >= PISTON_DEBOUNCE_MS:
            descore_open = not descore_open
            last_piston_toggle["Y"] = t
    prev["Y"] = y

    x = controller.buttonX.pressing()
    if x and not prev["X"]:
        if (t - last_piston_toggle["X"]) >= PISTON_DEBOUNCE_MS:
            trasero_open = not trasero_open
            last_piston_toggle["X"] = t
    prev["X"] = x

def compute_mechanism_setpoints(current_time: int) -> tuple:
    """Calcula setpoints de intake/cannon."""
    global override_cooldown_until

    r1 = controller.buttonR1.pressing()
    l1 = controller.buttonL1.pressing()

    if r1:
        override_cooldown_until = current_time + OVERRIDE_COOLDOWN_MS
        return (100, "FORWARD"), (100, "REVERSE")

    if l1:
        override_cooldown_until = current_time + OVERRIDE_COOLDOWN_MS
        return (100, "REVERSE"), (0, "STOP")

    in_cooldown = current_time < override_cooldown_until

    if intake_state == INTAKE_A_ON:
        pct = 50 if in_cooldown else 100
        return (pct, "FORWARD"), (30, "FORWARD")
    if intake_state == INTAKE_B_ON:
        pct = 50 if in_cooldown else 100
        return (pct, "REVERSE"), (0, "STOP")
    
    return (0, "STOP"), (0, "STOP")

# ================================================================
# CAPA 2: SAFETY & RELIABILITY
# ================================================================
def apply_anti_stall(intake_cmd: tuple, current_time: int) -> tuple:
    """Detecta atasco y aplica pulso reversa automático."""
    if not ANTI_STALL_ENABLED:
        return intake_cmd

    pct, direction = intake_cmd

    if direction == "STOP" or abs(pct) < STALL_CMD_MIN_PCT:
        stall["phase"] = "IDLE"
        stall["since_ms"] = 0
        return intake_cmd

    try:
        v1 = intake.velocity(RPM)
        v2 = intake_sup.velocity(RPM)
        v_abs = min(abs(v1), abs(v2))
    except:
        sensor_failures["intake_vel"] += 1
        return intake_cmd
    t = current_time

    if stall["phase"] == "IDLE":
        stall["phase"] = "DETECT"
        stall["since_ms"] = t
        stall["last_cmd_dir"] = direction
        return intake_cmd

    if stall["phase"] == "DETECT":
        if direction != stall["last_cmd_dir"]:
            stall["since_ms"] = t
            stall["last_cmd_dir"] = direction
            return intake_cmd

        elapsed = t - stall["since_ms"]
        if elapsed < STALL_GRACE_PERIOD_MS:
            return intake_cmd

        if v_abs <= STALL_SPEED_RPM and elapsed >= STALL_DETECT_MS:
            stall["phase"] = "PULSE_REV"
            stall["phase_until_ms"] = t + STALL_PULSE_REVERSE_MS
            return (100, "REVERSE" if direction == "FORWARD" else "FORWARD")

        if v_abs > STALL_SPEED_RPM + 10:
            stall["since_ms"] = t
        return intake_cmd

    if stall["phase"] == "PULSE_REV":
        if direction != stall["last_cmd_dir"]:
            stall["phase"] = "IDLE"
            stall["since_ms"] = t
            return intake_cmd
        
        if t < stall["phase_until_ms"]:
            return (100, "REVERSE" if stall["last_cmd_dir"] == "FORWARD" else "FORWARD")
        stall["phase"] = "PULSE_FWD"
        stall["phase_until_ms"] = t + STALL_PULSE_FORWARD_MS
        return (100, stall["last_cmd_dir"])

    if stall["phase"] == "PULSE_FWD":
        if direction != stall["last_cmd_dir"]:
            stall["phase"] = "IDLE"
            stall["since_ms"] = t
            return intake_cmd
        
        if t < stall["phase_until_ms"]:
            return (100, stall["last_cmd_dir"])
        stall["phase"] = "IDLE"
        stall["since_ms"] = t
        return intake_cmd

    return intake_cmd

# ================================================================
# CAPA 3: APPLY ACTUATORS
# ================================================================
def apply_drive(left_target: int, right_target: int):
    """Aplica setpoints de drivetrain."""
    slew_drive["L"] = slew_step(slew_drive["L"], left_target, SLEW_DRIVE_ACCEL, SLEW_DRIVE_DECEL)
    slew_drive["R"] = slew_step(slew_drive["R"], right_target, SLEW_DRIVE_ACCEL, SLEW_DRIVE_DECEL)

    if slew_drive["L"] != last_drive_cmd["L"]:
        v = slew_drive["L"]
        if v == 0:
            motor_left.stop()
        elif v > 0:
            motor_left.spin(FORWARD, v, PERCENT)
        else:
            motor_left.spin(REVERSE, abs(v), PERCENT)
        last_drive_cmd["L"] = v

    if slew_drive["R"] != last_drive_cmd["R"]:
        v = slew_drive["R"]
        if v == 0:
            motor_right.stop()
        elif v > 0:
            motor_right.spin(FORWARD, v, PERCENT)
        else:
            motor_right.spin(REVERSE, abs(v), PERCENT)
        last_drive_cmd["R"] = v

def apply_intake(cmd: tuple):
    """Aplica comando de intake."""
    global slew_intake_pct

    pct, direction = cmd

    der1 = temp_derate_pct("intake")
    der2 = temp_derate_pct("intake_sup")
    der = min(der1, der2)
    pct_derated = int(round(pct * der / 100.0))

    target_mag = 0 if direction == "STOP" else pct_derated
    
    slew_intake_pct = slew_step(slew_intake_pct, target_mag, SLEW_INTAKE_ACCEL, SLEW_INTAKE_DECEL)

    if slew_intake_pct == 0 or direction == "STOP":
        desired_dir = "STOP"
        desired_pct = 0
    else:
        desired_dir = direction
        desired_pct = slew_intake_pct

    if desired_pct == last_intake_cmd["pct"] and desired_dir == last_intake_cmd["dir"]:
        return

    if desired_dir == "STOP":
        intake.stop()
        intake_sup.stop()
    elif desired_dir == "FORWARD":
        intake.spin(FORWARD, desired_pct, PERCENT)
        intake_sup.spin(FORWARD, desired_pct, PERCENT)
    else:
        intake.spin(REVERSE, desired_pct, PERCENT)
        intake_sup.spin(REVERSE, desired_pct, PERCENT)

    last_intake_cmd["pct"] = desired_pct
    last_intake_cmd["dir"] = desired_dir

def apply_cannon(cmd: tuple):
    """Aplica comando de cañón."""
    global slew_cannon_pct, cannon_dir_state

    pct, desired_dir = cmd

    der = temp_derate_pct("cannon")
    pct = int(round(pct * der / 100.0))

    if (cannon_dir_state != "STOP" and desired_dir != "STOP" and desired_dir != cannon_dir_state):
        desired_dir = "STOP"

    target_mag = 0 if desired_dir == "STOP" else pct
    slew_cannon_pct = slew_step(slew_cannon_pct, target_mag, SLEW_CANNON_ACCEL, SLEW_CANNON_DECEL)

    if slew_cannon_pct == 0:
        final_dir = "STOP"
        cannon_dir_state = "STOP"
    else:
        final_dir = desired_dir
        cannon_dir_state = desired_dir

    if slew_cannon_pct == last_cannon_cmd["pct"] and final_dir == last_cannon_cmd["dir"]:
        return

    if final_dir == "STOP":
        cannon.stop()
    elif final_dir == "FORWARD":
        cannon.spin(FORWARD, slew_cannon_pct, PERCENT)
    else:
        cannon.spin(REVERSE, slew_cannon_pct, PERCENT)

    last_cannon_cmd["pct"] = slew_cannon_pct
    last_cannon_cmd["dir"] = final_dir

def apply_pistons():
    """Aplica estados de pistones."""
    piston_descores.set(descore_open)
    piston_trasero.set(trasero_open)

# ================================================================
# RUTINA AUTÓNOMA
# ================================================================
def autonomous_routine() -> None:
    """Rutina autónoma completa."""
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Iniciando autonomo...")
    
    # 1. Avanzar 49cm y activar pistón de descores
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 49cm...")
    drive_distance_cm(49, 50)
    piston_descores.set(True)
    wait(0.1, SECONDS)

    # 2. Girar 90 grados a la izquierda
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 90 grados...")
    turn_left_pivot_90(70)
    wait(0.2, SECONDS)

    # 3. Avanzar 23cm
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 23cm...")
    drive_distance_cm(23, 100)
    wait(0.2, SECONDS)

    # 4. Recoger pelotas
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Recogiendo pelotas...")
    
    intake.spin(FORWARD, 80, PERCENT)
    intake_sup.spin(FORWARD, 80, PERCENT)
    cannon.spin(FORWARD, 40, PERCENT)
    wait(0.2, SECONDS)

    # 4.2 Movimientos de sacudida
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Cargando pelotas...")
    
    optical_sensor.set_light_power(0, PERCENT)
    
    max_iterations = 20
    iteration_count = 0
    
    while not is_object_near() and iteration_count < max_iterations:
        motor_left.spin(FORWARD, 60, PERCENT)
        motor_right.spin(FORWARD, 60, PERCENT)
        wait(0.2, SECONDS)
        
        motor_left.spin(REVERSE, 60, PERCENT)
        motor_right.spin(REVERSE, 60, PERCENT)
        wait(0.2, SECONDS)
        
        iteration_count += 1
    
    # 4.3 Detener motores
    brain.screen.set_cursor(2, 1)
    if is_object_near():
        brain.screen.print("Carga completa!")
        wait(.2, SECONDS)
    else:
        brain.screen.print("Tiempo de carga terminado")
    
    intake.stop()
    intake_sup.stop()
    cannon.stop()
    motor_left.stop()
    motor_right.stop()
    wait(0.2, SECONDS)

    # 5. Girar 15 grados para alinear
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Alineando con porteria...")
    turn_right_degrees(15, 50)
    wait(0.2, SECONDS)
    
    # 6. Retroceder 50cm
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Retrocediendo 50cm...")
    drive_distance_cm(-50, 60)
    wait(0.2, SECONDS)

    motor_left.stop(HOLD)
    motor_right.stop(HOLD)

    # 7. Ensestar con filtrado de colores (EQUIPO Azul - rechaza Rojas)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Ensestando...")
    
    optical_sensor.set_light_power(100, PERCENT)
    
    max_cycles = 30
    cycle_count = 0
    enemy_detected = False
    
    # Lógica simplificada: siempre somos Azul, rechazamos Rojos
    while cycle_count < max_cycles and not enemy_detected:
        if is_red_detected():
            # DETENER: pelota enemiga detectada
            intake.stop()
            intake_sup.stop()
            brain.screen.set_cursor(3, 1)
            brain.screen.print("Pelota roja bloqueada!")
            wait(0.3, SECONDS)
            cannon.stop()
            enemy_detected = True
        else:
            # Continuar: dejar pasar pelotas azules
            intake.spin(FORWARD, 80, PERCENT)
            intake_sup.spin(FORWARD, 80, PERCENT)
            cannon.spin(REVERSE, 100, PERCENT)
        
        wait(0.1, SECONDS)
        cycle_count += 1
    
    # Detener todos los motores
    intake.stop()
    intake_sup.stop()
    cannon.stop()
    optical_sensor.set_light_power(0, PERCENT)

    brain.screen.set_cursor(2, 1)
    brain.screen.print("Autonomo completado")

# ================================================================
# FUNCIONES DE COMPETENCIA (ESTRUCTURA REQUERIDA POR FCS)
# ================================================================
def pre_auton():
    """
    Inicialización antes del autónomo.
    CRÍTICO: No debe contener bucles infinitos ni esperas largas.
    """
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Grande Robot v3.0")
    brain.screen.set_cursor(2, 1)
    brain.screen.print("EQUIPO: ROJO")
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Competencia Oficial")
    
    # Resetear encoders
    motor_left.reset_position()
    motor_right.reset_position()
    cannon.reset_position()
    intake.reset_position()
    intake_sup.reset_position()
    
    # Pistones en posición inicial
    piston_trasero.set(False)
    piston_descores.set(False)
    
    # Mostrar en controlador
    controller.screen.clear_screen()
    controller.screen.set_cursor(1, 1)
    controller.screen.print("EQUIPO: Azul")
    
    brain.screen.set_cursor(4, 1)
    brain.screen.print("Pre-auton completado")
    wait(0.5, SECONDS)

def autonomous():
    """
    Función autónoma - llamada por FCS cuando inicia el período autónomo.
    """
    autonomous_routine()

def user_control():
    """
    Función de control de usuario - llamada por FCS durante el período de driver.
    """
    global last_telemetry_ms, last_temp_sample_ms
    
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Driver Control Activo")

    last_telemetry_ms = now_ms()
    last_temp_sample_ms = now_ms()

    while True:
        cycle_start = now_ms()

        # Sample de temperaturas (cada 50ms)
        if (cycle_start - last_temp_sample_ms) >= 50:
            sample_temperatures()
            last_temp_sample_ms = cycle_start

        # Leer inputs y compute setpoints
        update_toggles()
        left_sp, right_sp = compute_drive_setpoints()
        intake_cmd, cannon_cmd = compute_mechanism_setpoints(cycle_start)

        # Safety layers
        intake_cmd = apply_anti_stall(intake_cmd, cycle_start)

        # Apply a motores físicos
        apply_drive(left_sp, right_sp)
        apply_intake(intake_cmd)
        apply_cannon(cannon_cmd)
        apply_pistons()

        # Telemetría (cada 100ms)
        if (cycle_start - last_telemetry_ms) >= 100:
            last_telemetry_ms = cycle_start
            
            brain.screen.set_cursor(2, 1)
            brain.screen.print("D:{} T:{} I:{}  ".format(
                "ON" if descore_open else "OFF",
                "ON" if trasero_open else "OFF",
                ["OFF", "A", "B"][intake_state]
            ))
            
            brain.screen.set_cursor(3, 1)
            brain.screen.print("In:{}{} Cn:{}{}  ".format(
                last_intake_cmd["dir"][0],
                last_intake_cmd["pct"],
                last_cannon_cmd["dir"][0],
                last_cannon_cmd["pct"]
            ))
            
            # Temperaturas
            brain.screen.set_cursor(4, 1)
            i_temp = max(temp_cache["intake"][0], temp_cache["intake_sup"][0])
            i_status = get_worst_status(temp_cache["intake"][1], temp_cache["intake_sup"][1])
            c_temp, c_status = temp_cache["cannon"]
            
            if i_status != "OK" or c_status != "OK":
                i_str = "ERR" if i_status == "ERR" else "{}{}".format(int(i_temp), i_status[0])
                c_str = "ERR" if c_status == "ERR" else "{}{}".format(int(c_temp), c_status[0])
                brain.screen.print("T:I{} C{}  ".format(i_str, c_str))
            else:
                brain.screen.print("                    ")
            
            # Errores de sensores
            total_errors = sum(sensor_failures.values())
            if total_errors > 0:
                brain.screen.set_cursor(5, 1)
                brain.screen.print("ERR V:{} I:{} Is:{} C:{}  ".format(
                    sensor_failures["intake_vel"],
                    sensor_failures["intake_temp"],
                    sensor_failures["intake_sup_temp"],
                    sensor_failures["cannon_temp"]
                ))
            else:
                brain.screen.set_cursor(5, 1)
                brain.screen.print("                    ")

        # Loop timing adaptativo
        elapsed = now_ms() - cycle_start
        wait(max(1, LOOP_TIME_MS - elapsed), MSEC)

# ================================================================
# CREAR INSTANCIA DE COMPETENCIA (REQUERIDO POR FCS)
# ================================================================
# CRÍTICO: Esta línea registra las funciones con el Field Control System
comp = Competition(user_control, autonomous)

# ================================================================
# INICIALIZACIÓN (SE EJECUTA AL CARGAR EL PROGRAMA)
# ================================================================
# Esta sección se ejecuta UNA VEZ al cargar el programa
# NO debe contener bucles infinitos
brain.screen.clear_screen()
brain.screen.set_cursor(1, 1)
brain.screen.print("Sistema Inicializado")
brain.screen.set_cursor(2, 1)
brain.screen.print("Esperando FCS...")

# Ejecutar pre_auton automáticamente
pre_auton()