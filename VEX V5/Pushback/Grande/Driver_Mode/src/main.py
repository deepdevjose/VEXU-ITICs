# =================================================================
# VEXcode – Configuración y Teleoperado (Grande – Modo manual v2.0)
# -----------------------------------------------------------------
# Autor: @deepdevjose (refactor asistido)
# =================================================================

from vex import *

# Import typing si está disponible (algunos firmwares VEX pueden no tenerlo)
try:
    from typing import Optional
except:
    Optional = None  # Fallback: no usar anotaciones Optional

# ------------------------------------------------
# Inicialización del cerebro y controlador
# ------------------------------------------------
brain = Brain()
controller = Controller()

# ------------------------------------------------
# CONFIGURACIÓN DE PUERTOS
# ------------------------------------------------
# Tren motriz (rojos 36:1)
DRIVE_LEFT_PORT   = Ports.PORT3
DRIVE_RIGHT_PORT  = Ports.PORT4

# Rampa/Intake (azul 6:1)
INTAKE_PORT = Ports.PORT20
INTAKE_SUP_PORT = Ports.PORT11

# Cañón (verde 18:1)
CANNON_PORT = Ports.PORT16

# ------------------------------------------------
# PARÁMETROS DE TUNING (ajustar en campo)
# ------------------------------------------------
# Loop timing
LOOP_TIME_MS = 20

# Deadzone por eje (mayor en turn para evitar drift)
DEADZONE_FWD = 5
DEADZONE_TURN = 8

# Curva exponencial (0.0=lineal, 0.5=balanceado, 1.0=cúbico)
EXPO_FWD = 0.5
EXPO_TURN = 0.4

# Slew rate (% cambio por ciclo de 20ms)
# Slew asimétrico: aceleración lenta, frenado rápido
SLEW_DRIVE_ACCEL = 8      # ~250ms para 0→100%
SLEW_DRIVE_DECEL = 15     # Frenado más rápido
SLEW_INTAKE_ACCEL = 25    # Más rápido para intake
SLEW_INTAKE_DECEL = 40    # Frenado muy rápido
SLEW_CANNON_ACCEL = 25
SLEW_CANNON_DECEL = 40

# Modo de frenado drivetrain (COAST=suave, BRAKE=preciso)
DRIVE_BRAKE_MODE = BrakeType.COAST

# Cooldown al soltar R1/L1 (ms sin aplicar toggles)
OVERRIDE_COOLDOWN_MS = 100  # Reducido: ya tenemos rampa suave

# Debounce para pistones (evitar doble toggle)
PISTON_DEBOUNCE_MS = 200

# Anti-atasco (stall detection)
ANTI_STALL_ENABLED = True
STALL_SPEED_RPM = 30        # Velocidad < 30 RPM = posible atasco
STALL_CMD_MIN_PCT = 70      # Solo detectar si comando ≥ 70%
STALL_DETECT_MS = 250       # Confirmar tras 250ms
STALL_GRACE_PERIOD_MS = 150 # Grace period tras arranque/cambio (evita falsos positivos)
# IMPORTANTE: GRACE_PERIOD_MS debe ser < DETECT_MS, sino nunca detecta
STALL_PULSE_REVERSE_MS = 180
STALL_PULSE_FORWARD_MS = 250

# Derating térmico (reducción por temperatura)
DERATING_ENABLED = True
TEMP_WARN_C = 50.0
TEMP_SOFT_C = 55.0
TEMP_HARD_C = 60.0
DERATE_SOFT = 85    # % potencia en zona soft
DERATE_HARD = 70    # % potencia en zona hard

# ------------------------------------------------
# Instancias de motores
# ------------------------------------------------
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_36_1, True)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_36_1, False)

intake = Motor(INTAKE_PORT, GearSetting.RATIO_6_1, False)
intake_sup = Motor(INTAKE_SUP_PORT, GearSetting.RATIO_6_1, True)

cannon = Motor(CANNON_PORT, GearSetting.RATIO_18_1, False)

# Pistones neumáticos
piston_trasero = DigitalOut(brain.three_wire_port.a)
piston_descores = DigitalOut(brain.three_wire_port.b)

# ------------------------------------------------
# Configuración de motores
# ------------------------------------------------
# Torque máximo (100% = sin límite artificial)
motor_left.set_max_torque(100, PERCENT)
motor_right.set_max_torque(100, PERCENT)
intake.set_max_torque(100, PERCENT)
intake_sup.set_max_torque(100, PERCENT)
cannon.set_max_torque(100, PERCENT)

# Modo de frenado
motor_left.set_stopping(DRIVE_BRAKE_MODE)
motor_right.set_stopping(DRIVE_BRAKE_MODE)
intake.set_stopping(BrakeType.BRAKE)
intake_sup.set_stopping(BrakeType.BRAKE)
cannon.set_stopping(BrakeType.BRAKE)

motor_left.set_velocity(100, PERCENT)
motor_right.set_velocity(100, PERCENT)

# ------------------------------------------------
# Constantes de estado (evita strings frágiles)
# ------------------------------------------------
INTAKE_OFF = 0
INTAKE_A_ON = 1  # intake fwd 100% + cannon fwd 30%
INTAKE_B_ON = 2  # intake rev 100%, cannon off

# ------------------------------------------------
# Variables de estado global
# ------------------------------------------------
# Pistones
descore_open = False
trasero_open = False
last_piston_toggle = {"Y": 0, "X": 0}  # Timestamp de último toggle

# Toggles
intake_state = INTAKE_OFF
prev = {"R1": False, "L1": False, "A": False, "B": False, "Y": False, "X": False}

# Estado de dirección para rampa segura en cannon
cannon_dir_state = "STOP"  # Actual dirección física del cannon

# Slew state (valores actuales tras rampa)
slew_drive = {"L": 0, "R": 0}
slew_intake_pct = 0
slew_cannon_pct = 0

# Cache de comandos aplicados (anti-spam)
last_drive_cmd = {"L": 0, "R": 0}
last_intake_cmd = {"pct": 0, "dir": "STOP"}
last_cannon_cmd = {"pct": 0, "dir": "STOP"}

# Override R1/L1
override_cooldown_until = 0

# Anti-stall state machine
stall = {
    "phase": "IDLE",        # IDLE / DETECT / PULSE_REV / PULSE_FWD
    "since_ms": 0,
    "phase_until_ms": 0,
    "last_cmd_dir": "STOP",
}

# Telemetría
last_telemetry_ms = 0
last_temp_sample_ms = 0  # Timestamp de último sample de temperatura
sensor_failures = {
    "intake_temp": 0,      # Intake principal
    "intake_sup_temp": 0,  # Intake superior (separado para diagnóstico)
    "cannon_temp": 0, 
    "intake_vel": 0
}

# Cache de lecturas de sensores (sample cada 50ms, más frecuente que telemetría)
temp_cache = {
    "intake": (0, "OK"), 
    "intake_sup": (0, "OK"),  # Cache separado para intake_sup
    "cannon": (0, "OK")
}

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

def slew_step(current: int, target: int, step_accel: int, step_decel = None) -> int:
    """Slew asimétrico robusto (maneja cruces de 0 correctamente)."""
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

    # Misma dirección (o uno es 0): decidir por magnitud
    if abs(target) > abs(current):
        step = step_accel
    else:
        step = step_decel

    if current < target:
        return min(current + step, target)
    else:
        return max(current - step, target)

def temp_derate_pct(motor_name: str) -> int:
    """Retorna factor de reducción (%) según temperatura del motor.
    Usa cache de temp_cache (sin side effects de lectura).
    """
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
    """Retorna (temperatura, estado) donde estado es 'OK', 'WARN', 'SOFT', 'HARD', o 'ERR'."""
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
    """Sample de temperaturas cada ~50ms (más frecuente que telemetría).
    Evita lecturas redundantes y garantiza consistencia entre control y display.
    """
    global temp_cache
    
    # Helper para clasificar temperatura
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
    
    # Intake superior (separado para derating correcto)
    try:
        t = intake_sup.temperature()
        temp_cache["intake_sup"] = (t, classify_temp(t))
    except:
        sensor_failures["intake_sup_temp"] += 1  # Contador separado
        temp_cache["intake_sup"] = (0, "ERR")
    
    # Cannon
    try:
        t = cannon.temperature()
        temp_cache["cannon"] = (t, classify_temp(t))
    except:
        sensor_failures["cannon_temp"] += 1
        temp_cache["cannon"] = (0, "ERR")

def get_worst_status(status1: str, status2: str) -> str:
    """Retorna el peor status térmico por severidad (para display correcto)."""
    severity = {"ERR": 0, "HARD": 4, "SOFT": 3, "WARN": 2, "OK": 1}
    s1_sev = severity.get(status1, 0)
    s2_sev = severity.get(status2, 0)
    return status1 if s1_sev >= s2_sev else status2

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
    """Actualiza estados de toggles (A, B, Y, X) con debounce en pistones."""
    global intake_state, descore_open, trasero_open
    
    t = now_ms()  # Lectura local para debounce

    a = controller.buttonA.pressing()
    if a and not prev["A"]:
        intake_state = INTAKE_OFF if intake_state == INTAKE_A_ON else INTAKE_A_ON
    prev["A"] = a

    b = controller.buttonB.pressing()
    if b and not prev["B"]:
        intake_state = INTAKE_OFF if intake_state == INTAKE_B_ON else INTAKE_B_ON
    prev["B"] = b

    # Pistones con debounce (evita doble toggle por rebote humano)
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
    """Calcula setpoints de intake/cannon con prioridad override > toggles.
    Retorna: (intake_cmd, cannon_cmd)
    donde cmd = (pct, dir) con dir in ["FORWARD", "REVERSE", "STOP"]
    """
    global override_cooldown_until

    r1 = controller.buttonR1.pressing()
    l1 = controller.buttonL1.pressing()

    # Prioridad 1: Override R1/L1 (control directo)
    # NOTA: R1 = intake FWD + cannon REV (shoot/fire)
    #       L1 = intake REV + cannon OFF (unjam/reverse)
    # Verificar que coincide con driver intent antes de torneo
    if r1:
        override_cooldown_until = current_time + OVERRIDE_COOLDOWN_MS
        return (100, "FORWARD"), (100, "REVERSE")

    if l1:
        override_cooldown_until = current_time + OVERRIDE_COOLDOWN_MS
        return (100, "REVERSE"), (0, "STOP")

    # Cooldown mejorado: en vez de STOP, retorna suavemente al toggle
    # Esto evita el "lag" percibido al soltar override
    in_cooldown = current_time < override_cooldown_until

    # Prioridad 2: Toggles A/B (con rampa durante cooldown)
    if intake_state == INTAKE_A_ON:
        pct = 50 if in_cooldown else 100  # Rampa suave en cooldown
        return (pct, "FORWARD"), (30, "FORWARD")  # 30% para mejor consistencia
    if intake_state == INTAKE_B_ON:
        pct = 50 if in_cooldown else 100
        return (pct, "REVERSE"), (0, "STOP")
    
    return (0, "STOP"), (0, "STOP")

# ================================================================
# CAPA 2: Safety & Reliability (anti-stall)
# ================================================================
def apply_anti_stall(intake_cmd: tuple, current_time: int) -> tuple:
    """Detecta atasco y aplica pulso reversa automático.
    State machine: IDLE → DETECT → PULSE_REV → PULSE_FWD → IDLE
    """
    if not ANTI_STALL_ENABLED:
        return intake_cmd

    pct, direction = intake_cmd

    # Solo aplica si hay comando fuerte
    if direction == "STOP" or abs(pct) < STALL_CMD_MIN_PCT:
        stall["phase"] = "IDLE"
        stall["since_ms"] = 0
        return intake_cmd

    # Medir velocidad real de AMBOS motores en RPM (más confiable que PERCENT)
    try:
        v1 = intake.velocity(RPM)
        v2 = intake_sup.velocity(RPM)
        v_abs = min(abs(v1), abs(v2))  # Si uno está atascado, lo detectamos
    except:
        sensor_failures["intake_vel"] += 1
        return intake_cmd
    t = current_time  # Usar timestamp pasado

    if stall["phase"] == "IDLE":
        stall["phase"] = "DETECT"
        stall["since_ms"] = t
        stall["last_cmd_dir"] = direction
        return intake_cmd

    if stall["phase"] == "DETECT":
        # Si cambió dirección, reinicia con grace period
        if direction != stall["last_cmd_dir"]:
            stall["since_ms"] = t
            stall["last_cmd_dir"] = direction
            return intake_cmd

        # Grace period: esperar un poco tras arranque antes de detectar stall
        elapsed = t - stall["since_ms"]
        if elapsed < STALL_GRACE_PERIOD_MS:
            return intake_cmd

        # Detectar stall sostenido (solo después del grace period)
        if v_abs <= STALL_SPEED_RPM and elapsed >= STALL_DETECT_MS:
            stall["phase"] = "PULSE_REV"
            stall["phase_until_ms"] = t + STALL_PULSE_REVERSE_MS
            # Pulso reversa
            return (100, "REVERSE" if direction == "FORWARD" else "FORWARD")

        # Motor OK: refresca timer
        if v_abs > STALL_SPEED_RPM + 10:
            stall["since_ms"] = t
        return intake_cmd

    if stall["phase"] == "PULSE_REV":
        # Si driver cambia comando durante pulso, abortar y resetear
        if direction != stall["last_cmd_dir"]:
            stall["phase"] = "IDLE"
            stall["since_ms"] = t
            return intake_cmd
        
        if t < stall["phase_until_ms"]:
            # Mantener reversa
            return (100, "REVERSE" if stall["last_cmd_dir"] == "FORWARD" else "FORWARD")
        # Pasar a forward
        stall["phase"] = "PULSE_FWD"
        stall["phase_until_ms"] = t + STALL_PULSE_FORWARD_MS
        return (100, stall["last_cmd_dir"])

    if stall["phase"] == "PULSE_FWD":
        # Si driver cambia comando durante pulso, abortar y resetear
        if direction != stall["last_cmd_dir"]:
            stall["phase"] = "IDLE"
            stall["since_ms"] = t
            return intake_cmd
        
        if t < stall["phase_until_ms"]:
            return (100, stall["last_cmd_dir"])
        # Fin del ciclo
        stall["phase"] = "IDLE"
        stall["since_ms"] = t
        return intake_cmd

    return intake_cmd

# ================================================================
# CAPA 3: Apply Actuators (físico con cache, slew, derating)
# ================================================================
def apply_drive(left_target: int, right_target: int):
    """Aplica setpoints de drivetrain con slew asimétrico y dirección explícita."""
    slew_drive["L"] = slew_step(slew_drive["L"], left_target, SLEW_DRIVE_ACCEL, SLEW_DRIVE_DECEL)
    slew_drive["R"] = slew_step(slew_drive["R"], right_target, SLEW_DRIVE_ACCEL, SLEW_DRIVE_DECEL)

    # Anti-spam + dirección explícita (sin valores negativos en spin)
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
    """Aplica comando de intake con slew, derating térmico y anti-spam.
    Lógica mejorada: dirección y magnitud tienen fuente única de verdad.
    """
    global slew_intake_pct

    pct, direction = cmd

    # Derating térmico (usar cache de AMBOS motores - el peor caso)
    der1 = temp_derate_pct("intake")
    der2 = temp_derate_pct("intake_sup")  # Ahora sí usa cache separado
    der = min(der1, der2)  # El peor de los dos
    pct_derated = int(round(pct * der / 100.0))

    # Determinar magnitud objetivo (siempre positiva)
    target_mag = 0 if direction == "STOP" else pct_derated
    
    # Slew rate asimétrico
    slew_intake_pct = slew_step(slew_intake_pct, target_mag, SLEW_INTAKE_ACCEL, SLEW_INTAKE_DECEL)

    # Derivar dirección final: STOP solo si magnitud es 0
    if slew_intake_pct == 0 or direction == "STOP":
        desired_dir = "STOP"
        desired_pct = 0
    else:
        desired_dir = direction
        desired_pct = slew_intake_pct

    # Anti-spam
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
    """Aplica comando de cañón con gate de dirección: si invierte, primero va a STOP.
    Evita slam mecánico con máquina de estados simple.
    
    NOTA: Si el driver hace 'tap' rápido para invertir, el cañón puede quedarse en STOP
    (necesita mantener el comando hasta que rampa a 0 y luego invierte).
    """
    global slew_cannon_pct, cannon_dir_state

    pct, desired_dir = cmd

    # Derating térmico (usar cache)
    der = temp_derate_pct("cannon")
    pct = int(round(pct * der / 100.0))

    # Gate: si pide invertir mientras estaba girando, primero ir a STOP
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

    # Anti-spam
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
    """Aplica estados de pistones neumáticos."""
    piston_descores.set(descore_open)
    piston_trasero.set(trasero_open)

# ================================================================
# Inicialización
# ================================================================
def init_positions():
    """Posiciones iniciales seguras y sincronización de variables."""
    global descore_open, trasero_open
    
    cannon.reset_position()
    cannon.stop()
    
    # Sincronizar hardware con variables
    descore_open = False
    trasero_open = False
    piston_descores.set(False)
    piston_trasero.set(False)

# ================================================================
# Bucle principal
# ================================================================
def main():
    """Loop principal de teleoperado."""
    global last_telemetry_ms, last_temp_sample_ms

    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Grande Robot v2.0")

    init_positions()
    last_telemetry_ms = now_ms()
    last_temp_sample_ms = now_ms()

    while True:
        # Sample único de tiempo al inicio del ciclo (evita jitter y lecturas inconsistentes)
        cycle_start = now_ms()

        # 1) Sample de temperaturas (cada 50ms, independiente de telemetría)
        if (cycle_start - last_temp_sample_ms) >= 50:
            sample_temperatures()
            last_temp_sample_ms = cycle_start

        # 2) Leer inputs y compute setpoints
        update_toggles()
        left_sp, right_sp = compute_drive_setpoints()
        intake_cmd, cannon_cmd = compute_mechanism_setpoints(cycle_start)

        # 3) Safety layers
        intake_cmd = apply_anti_stall(intake_cmd, cycle_start)

        # 4) Apply a motores físicos
        apply_drive(left_sp, right_sp)
        apply_intake(intake_cmd)
        apply_cannon(cannon_cmd)
        apply_pistons()

        # 5) Telemetría estable (cada 100ms, sin jitter)
        if (cycle_start - last_telemetry_ms) >= 100:
            last_telemetry_ms = cycle_start
            
            # Ya no llamamos sample_temperatures aquí (se hace cada 50ms arriba)
            
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
            
            # Mostrar temperaturas y estado de derating (desde WARN=50°C)
            brain.screen.set_cursor(4, 1)
            # Elegir peor temperatura y peor status entre intake e intake_sup
            i_temp = max(temp_cache["intake"][0], temp_cache["intake_sup"][0])
            i_status = get_worst_status(temp_cache["intake"][1], temp_cache["intake_sup"][1])
            c_temp, c_status = temp_cache["cannon"]
            
            if i_status != "OK" or c_status != "OK":
                # Formato claro: I55W=Intake 55°C Warning, ERR explícito
                i_str = "ERR" if i_status == "ERR" else "{}{}".format(int(i_temp), i_status[0])
                c_str = "ERR" if c_status == "ERR" else "{}{}".format(int(c_temp), c_status[0])
                brain.screen.print("T:I{} C{}  ".format(i_str, c_str))
            else:
                brain.screen.print("                    ")
            
            # Mostrar errores de sensores solo si hay fallos (con separadores para legibilidad)
            total_errors = sum(sensor_failures.values())
            if total_errors > 0:
                brain.screen.set_cursor(5, 1)
                # Agregar intake_sup a telemetría (Is = intake_sup)
                brain.screen.print("ERR V:{} I:{} Is:{} C:{}  ".format(
                    sensor_failures["intake_vel"],
                    sensor_failures["intake_temp"],
                    sensor_failures["intake_sup_temp"],
                    sensor_failures["cannon_temp"]
                ))
            else:
                brain.screen.set_cursor(5, 1)
                brain.screen.print("                    ")

        # 6) Loop timing adaptativo
        elapsed = now_ms() - cycle_start
        wait(max(1, LOOP_TIME_MS - elapsed), MSEC)

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()
