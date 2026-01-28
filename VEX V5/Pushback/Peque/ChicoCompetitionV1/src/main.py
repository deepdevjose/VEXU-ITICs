# ---------------------------------------------------------------------------- #
#                                                                              #
# 	Module:       main.py                                                      #
# 	Author:       Josee                                                        #
# 	Created:      1/27/2026, 6:12:07 PM                                        #
# 	Description:  V5 project                                                   #
#                                                                              #
# ---------------------------------------------------------------------------- #

# Library imports
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
DEADZONE_STRAFE = 3  # Deadzone muy pequeño para precisión máxima en axis 1

# Curva exponencial (0.0=lineal, 0.5=balanceado, 1.0=cúbico)
EXPO_FWD = 0.5
EXPO_TURN = 0.4
EXPO_STRAFE = 0.6  # Mayor curva exponencial para control ultra-preciso

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
# PARÁMETROS DE ODOMETRÍA
# ------------------------------------------------
# Medidas de las llantas para odometría precisa
WHEEL_DIAMETER_CM = 10.0       # Diámetro de la llanta: 10cm
WHEEL_TRAVEL_CM = 32.0         # 1 vuelta completa = 32cm recorridos
WHEEL_DEGREES = 354.0          # 1 vuelta completa = 354 grados en encoder

# Conversión: grados por centímetro
DEGREES_PER_CM = WHEEL_DEGREES / WHEEL_TRAVEL_CM  # 354/32 = 11.0625 grados/cm

# ------------------------------------------------
# PARÁMETROS DE DETECCIÓN DE BLOQUEO
# ------------------------------------------------
STALL_THRESHOLD_DEGREES = 5.0   # Movimiento mínimo esperado en 0.5s
STALL_CHECK_INTERVAL = 0.5      # Intervalo de verificación en segundos
MAX_RETRY_TIME = 2.0            # Tiempo de retry a máxima potencia
BLOCKED_ALERT_DURATION = 3.0    # Duración de la alerta cuando está bloqueado

# ------------------------------------------------
# Instancias de motores
# ------------------------------------------------
# Drivetrain: reversed en constructor según montaje físico
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_18_1, False)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_18_1, True)

# Brushes: invertidos para semántica pura (FORWARD=recolectar, REVERSE=expulsar)
brush_front  = Motor(BRUSH_FRONT_PORT,  GearSetting.RATIO_18_1, True)
brush_bottom = Motor(BRUSH_BOTTOM_PORT, GearSetting.RATIO_18_1, True)

# Cannon/WAY: ajustar reversed para que FORWARD=disparar, REVERSE=unjam
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
unload_mode = False  # Toggle R2 para descarga de loader
prev = {"R2": False, "L1": False, "L2": False, "A": False, "B": False, "Y": False, "X": False}

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

# Override R2/L1
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
# Funciones de Movimiento Autónomo con Odometría
# ================================================================
def drive_distance_cm(distance_cm: float, velocity: int = 50) -> None:
    """Mueve el robot una distancia específica en centímetros usando odometría.
    
    Incluye detección de bloqueo al ir hacia atrás:
    - Si se detecta bloqueo, intenta con máxima potencia por 2s
    - Si sigue bloqueado, enciende alerta visual/sonora y avanza hacia adelante
    
    Args:
        distance_cm: Distancia a recorrer en centímetros (+ adelante, - atrás)
        velocity: Velocidad del movimiento (0-100%), por defecto 50%
    """
    # Calcular grados necesarios para la distancia deseada
    degrees_to_turn = distance_cm * DEGREES_PER_CM
    
    # Resetear encoders antes del movimiento
    motor_left.reset_position()
    motor_right.reset_position()
    
    # Determinar dirección
    direction = FORWARD if distance_cm > 0 else REVERSE
    degrees_abs = abs(degrees_to_turn)
    
    # Si va hacia atrás, usar detección de bloqueo
    if distance_cm < 0:
        drive_backward_with_stall_detection(degrees_abs, velocity)
    else:
        # Movimiento normal hacia adelante
        motor_left.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, False)
        motor_right.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, True)


def drive_backward_with_stall_detection(degrees_target: float, velocity: int) -> None:
    """Mueve el robot hacia atrás con detección de bloqueo.
    
    Si detecta que el robot se atascó (no avanza):
    1. Intenta con máxima potencia por 2 segundos
    2. Si sigue atascado, enciende pitillo (alerta) y avanza hacia adelante
    
    Args:
        degrees_target: Grados totales a recorrer hacia atrás
        velocity: Velocidad inicial del movimiento (0-100%)
    """
    # Iniciar movimiento hacia atrás
    motor_left.spin(REVERSE, velocity, PERCENT)
    motor_right.spin(REVERSE, velocity, PERCENT)
    
    # Variables para detección de bloqueo
    last_position = 0
    elapsed_time = 0.0
    check_interval = STALL_CHECK_INTERVAL
    
    while elapsed_time < 10.0:  # Timeout general de 10 segundos
        wait(check_interval, SECONDS)
        elapsed_time += check_interval
        
        # Obtener posición promedio actual
        current_position = abs((motor_left.position(DEGREES) + motor_right.position(DEGREES)) / 2)
        
        # Verificar si ya alcanzamos el objetivo
        if current_position >= degrees_target:
            motor_left.stop()
            motor_right.stop()
            return
        
        # Detectar bloqueo: si no se movió lo suficiente
        movement = abs(current_position - last_position)
        if movement < STALL_THRESHOLD_DEGREES:
            # ¡BLOQUEADO! Intentar con máxima potencia
            brain.screen.set_cursor(3, 1)
            brain.screen.print("BLOQUEADO! Retry...")
            
            # Guardar posición actual antes del retry
            retry_start_pos = current_position
            
            # Intentar con 100% de potencia por 2 segundos
            motor_left.spin(REVERSE, 100, PERCENT)
            motor_right.spin(REVERSE, 100, PERCENT)
            wait(MAX_RETRY_TIME, SECONDS)
            
            # Verificar si logró avanzar
            retry_end_pos = abs((motor_left.position(DEGREES) + motor_right.position(DEGREES)) / 2)
            retry_movement = abs(retry_end_pos - retry_start_pos)
            
            if retry_movement < STALL_THRESHOLD_DEGREES:
                # Sigue bloqueado: activar alerta y cambiar dirección
                motor_left.stop()
                motor_right.stop()
                
                brain.screen.set_cursor(3, 1)
                brain.screen.print("ATASCADO! Alerta ON")
                
                # Encender pitillo (alerta visual en pantalla)
                brain.screen.set_pen_color(Color.RED)
                brain.screen.draw_rectangle(0, 0, 480, 240)
                
                # Esperar para que sea visible
                wait(BLOCKED_ALERT_DURATION, SECONDS)
                
                # Cambiar dirección: avanzar hacia adelante
                brain.screen.set_cursor(3, 1)
                brain.screen.print("Yendo adelante...")
                brain.screen.set_pen_color(Color.WHITE)
                
                motor_left.spin(FORWARD, 50, PERCENT)
                motor_right.spin(FORWARD, 50, PERCENT)
                wait(1.0, SECONDS)
                
                motor_left.stop()
                motor_right.stop()
                return
            else:
                # El retry funcionó, continuar
                brain.screen.set_cursor(3, 1)
                brain.screen.print("Retry exitoso!")
                motor_left.spin(REVERSE, velocity, PERCENT)
                motor_right.spin(REVERSE, velocity, PERCENT)
        
        last_position = current_position
    
    # Timeout alcanzado
    motor_left.stop()
    motor_right.stop()

def turn_left_degrees(degrees: float) -> None:
    """Gira el robot a la izquierda sobre su propio eje.
    
    Realiza un giro en el lugar (tank turn) rotando ambas llantas
    en direcciones opuestas a velocidad fija del 50%.
    
    Args:
        degrees: Ángulo aproximado de giro en grados.
                 Nota: La conversión tiempo/grados es una aproximación.
    
    Note:
        Esta es una función legacy basada en tiempo, no en odometría.
        Para giros precisos, considerar usar turn_left_pivot_XX().
    """
    duration = degrees / 100.0
    motor_left.spin(REVERSE, 50, PERCENT)
    motor_right.spin(FORWARD, 50, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_right_degrees(degrees: float) -> None:
    """Gira el robot a la derecha sobre su propio eje.
    
    Realiza un giro en el lugar (tank turn) rotando ambas llantas
    en direcciones opuestas a velocidad fija del 50%.
    
    Args:
        degrees: Ángulo aproximado de giro en grados.
                 Nota: La conversión tiempo/grados es una aproximación.
    
    Note:
        Esta es una función legacy basada en tiempo, no en odometría.
        Para giros precisos, considerar implementar turn_right_pivot_XX().
    """
    duration = degrees / 100.0
    motor_left.spin(FORWARD, 50, PERCENT)
    motor_right.spin(REVERSE, 50, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_left_pivot_50(velocity: int = 50) -> None:
    """Gira aproximadamente 50 grados a la izquierda con pivote estacionario.
    
    Realiza un giro pivotando sobre la llanta izquierda (permanece frenada)
    mientras la llanta derecha avanza 18cm, resultando en ~50° de rotación.
    Utiliza odometría precisa basada en encoders.
    
    Args:
        velocity: Velocidad de giro (0-100%), por defecto 50%.
    
    Proceso:
        1. Resetea encoder derecho a posición 0
        2. Frena llanta izquierda como punto de pivote
        3. Mueve llanta derecha 199 grados (~18cm)
        4. Frena ambas llantas al finalizar
    
    Note:
        Conversión: 18cm × 11.0625 grados/cm ≈ 199 grados de encoder.
    """
    # Distancia que debe recorrer la llanta derecha para girar 50 grados
    pivot_distance_cm = 18.0
    degrees_to_turn = pivot_distance_cm * DEGREES_PER_CM  # 18 * 11.0625 = 199 grados
    
    # PASO 1: Resetear encoder de la llanta derecha para empezar en 0
    motor_right.reset_position()
    
    # PASO 2: Frenar la llanta izquierda (aplicar brake como pivote)
    motor_left.stop(BrakeType.BRAKE)
    
    # PASO 3: Mover solo la llanta derecha hacia adelante 177 grados desde 0
    motor_right.spin_for(FORWARD, degrees_to_turn, DEGREES, velocity, PERCENT, True)
    
    # PASO 4: Frenar ambas llantas al terminar
    motor_left.stop(BrakeType.BRAKE)
    motor_right.stop(BrakeType.BRAKE)

def turn_left_pivot_55(velocity: int = 50) -> None:
    """Gira aproximadamente 55 grados a la izquierda con pivote estacionario.
    
    Realiza un giro pivotando sobre la llanta izquierda (permanece frenada)
    mientras la llanta derecha avanza 22.5cm, resultando en ~55° de rotación.
    Utiliza odometría precisa basada en encoders.
    
    Args:
        velocity: Velocidad de giro (0-100%), por defecto 50%.
    
    Proceso:
        1. Resetea encoder derecho a posición 0
        2. Frena llanta izquierda como punto de pivote
        3. Mueve llanta derecha 249 grados (~22.5cm)
        4. Frena ambas llantas al finalizar
    
    Note:
        Conversión: 22.5cm × 11.0625 grados/cm ≈ 249 grados de encoder.
        Se usa para giros más amplios que turn_left_pivot_50().
    """
    # Distancia que debe recorrer la llanta derecha para girar 50 grados
    pivot_distance_cm = 22.5
    degrees_to_turn = pivot_distance_cm * DEGREES_PER_CM  # 16 * 11.0625 = 177 grados
    
    # PASO 1: Resetear encoder de la llanta derecha para empezar en 0
    motor_right.reset_position()
    
    # PASO 2: Frenar la llanta izquierda (aplicar brake como pivote)
    motor_left.stop(BrakeType.BRAKE)
    
    # PASO 3: Mover solo la llanta derecha hacia adelante 177 grados desde 0
    motor_right.spin_for(FORWARD, degrees_to_turn, DEGREES, velocity, PERCENT, True)
    
    # PASO 4: Frenar ambas llantas al terminar
    motor_left.stop(BrakeType.BRAKE)
    motor_right.stop(BrakeType.BRAKE)

# ================================================================
# CAPA 1: Compute Setpoints (lógica de control)
# ================================================================
def compute_drive_setpoints() -> tuple:
    """Calcula setpoints de drivetrain con expo, deadzone y mezcla arcade.
    Axis 4 (izquierdo horizontal) y Axis 1 (derecho horizontal) ambos controlan giro.
    Axis 1 tiene control ultra-preciso para ajustes finos.
    Retorna: (left_pct, right_pct)
    """
    fwd = deadband(controller.axis3.position(), DEADZONE_FWD)
    turn = deadband(controller.axis4.position(), DEADZONE_TURN)
    strafe = deadband(controller.axis1.position(), DEADZONE_STRAFE)  # Axis 1 para giro preciso

    fwd = expo(fwd, EXPO_FWD)
    turn = expo(turn, EXPO_TURN)
    strafe = expo(strafe, EXPO_STRAFE)  # Control exponencial para máxima precisión

    # Combinar ambos ejes de giro (axis 4 + axis 1)
    combined_turn = clamp(turn + strafe)

    left = clamp(fwd + combined_turn)
    right = clamp(fwd - combined_turn)
    return left, right

def update_toggles():
    """Actualiza estados de toggles (A, B, Y, X, R2).
    Bloquea A/B durante cooldown para que override sea modo exclusivo.
    """
    global brush_state, tumbaburros_extended, ramp_extended, unload_mode

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

    # Toggle X para rampa (sube/baja)
    x = controller.buttonX.pressing()
    if x and not prev["X"]:
        ramp_extended = not ramp_extended
    prev["X"] = x

    # Toggle L2 para modo descarga de loader
    l2 = controller.buttonL2.pressing()
    if l2 and not prev["L2"]:
        unload_mode = not unload_mode
        # Al activar descarga, bajar tumbaburros automáticamente
        if unload_mode:
            tumbaburros_extended = True
    prev["L2"] = l2

def compute_mechanism_setpoints() -> tuple:
    """Calcula setpoints de cannon/way/brushes con prioridad override > unload_mode > toggles.
    Retorna: (brush_cmd, cannon_cmd, way_cmd)
    donde cmd = (pct, dir) con dir in ["FORWARD", "REVERSE", "STOP"]
    """
    global override_cooldown_until

    r2 = controller.buttonR2.pressing()
    l1 = controller.buttonL1.pressing()

    # Prioridad 1: Override R2/L1 (control directo)
    if l1:
        override_cooldown_until = now_ms() + OVERRIDE_COOLDOWN_MS
        return (100, "REVERSE"), (100, "REVERSE"), (100, "REVERSE")

    if r2:
        override_cooldown_until = now_ms() + OVERRIDE_COOLDOWN_MS
        return (100, "FORWARD"), (100, "FORWARD"), (100, "FORWARD")

    # Cooldown: cannon/way STOP, brushes mantienen toggle
    if now_ms() < override_cooldown_until:
        brush_cmd = get_toggle_brush_cmd()
        return brush_cmd, (0, "STOP"), (0, "STOP")

    # Prioridad 2: Modo descarga (R2 toggle) - brushes y way en forward
    if unload_mode:
        return (100, "FORWARD"), (0, "STOP"), (100, "FORWARD")

    # Prioridad 3: Toggles A/B (solo brushes, cannon/way detenidos)
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
    motor_left.reset_position()
    motor_right.reset_position()
    cannon.reset_position()
    cannon.stop()
    way.reset_position()
    way.stop()
    ramp_piston.set(False)
    tumbaburros.set(False)

# ================================================================
# Rutina Autónoma
# ================================================================
def autonomous_routine() -> None:
    """Ejecuta la rutina autónoma completa del robot.
    
    Secuencia de 15 pasos diseñada para:
        1. Avanzar hacia la portería más cercana
        2. Posicionarse y anotar con los cepillos
        3. Desplazarse por el campo activando tumbaburros
        4. Finalizar en posición estratégica
    
    Pasos principales:
        - Avance inicial de 114cm hacia portería
        - Giro y posicionamiento para anotación
        - Expulsión de pelota con cepillos (2s)
        - Navegación por campo con giros pivotantes
        - Activación/desactivación de tumbaburros
        - Retroceso final de 155cm
        - Posicionamiento final con doble giro de 45°
    
    Note:
        Todos los movimientos incluyen pausas de estabilización (0.1-0.5s)
        para asegurar precisión en la ejecución secuencial.
    
    Displays:
        Muestra progreso en pantalla del brain durante cada paso.
    """
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Iniciando autonomo...")

        
    # 1. Avanzar 118cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 114cm...")
    drive_distance_cm(114, 50)  # 114cm a 50% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar
    
    # 2. Girar 45 grados a la izquierda (pivote sobre llanta izquierda)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 45 grados...")
    turn_left_pivot_55(50)  # Girar a 50% velocidad

    # 3. Avanzar otros 2cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 1cm...")
    drive_distance_cm(1, 10)  # 1cm a 10% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 4. Frenar el robot y activar motores en REVERSE para aventar pelota
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Aventando pelota...")
    
    # Frenar el drivetrain para que no se mueva
    motor_left.stop(BrakeType.BRAKE)
    motor_right.stop(BrakeType.BRAKE)
    
    # Activar way, brushes y cannon en REVERSE para aventar pelota por abajo
    brush_front.spin(REVERSE, 25, PERCENT)
    brush_bottom.spin(REVERSE, 20, PERCENT)

    # Mantener girando por 2 segundos
    wait(2.0, SECONDS)
    
    # Detener todos los motores de aventar
    brush_front.stop()
    brush_bottom.stop()

    wait(0.1, SECONDS)  # Pausa para estabilizar

    #4.5. Retroceder 10cm para despejar
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Retrocediendo 20cm...")
    drive_distance_cm(-20, 20)  # 20cm atrás a 20% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 5. Girar hacia izquierda 45 grados más (pivote sobre llanta izquierda)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 55 grados...")
    turn_left_pivot_55(50)  # Girar a 50% velocidad

    # 6. Avanzar otros 15cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 15cm...")
    drive_distance_cm(15, 20)  # 15cm a 20% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 7. Girar 90 grados a la izquierda (pivote sobre llanta IZQUIERDA)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 90 grados...")
    for _ in range(2):
        turn_left_pivot_55(50)  # Girar a 50% velocidad    

    # 8. Avanzar otros 90cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 90cm...")
    drive_distance_cm(50, 90)  # 90cm a 90% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 9. Avanzar otros 90cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 90cm...")
    drive_distance_cm(5, 40)  # 90cm a 90% velocidad
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 10. Activar TUMBABURROS
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Activando tumbaburros...")
    tumbaburros.set(True)
    wait(1.0, SECONDS)  # Esperar a que baje

   # 11. Girar 90 grados a la derecha con la funcion legacy
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 90 grados...")
    turn_right_degrees(68)  # Girar 90 grados a la derecha
    wait(0.5, SECONDS)  # Pausa para estabilizar
    
   # 12. Desactivar tumbaburros 
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Desactivando tumbaburros...")
    tumbaburros.set(False)
    wait(0.5, SECONDS)  # Pausa para estabilizar

    # 14. Retroceder para alinearse al cargador
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Retrocediendo 30cm...")
    drive_distance_cm(-123, 50)  # 30cm atrás a 50% velocidad
    wait(0.5, SECONDS)  # Pausa para estabilizar

    # 16. Bajar el tumbaburros para cargar
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Bajando tumbaburros...")
    tumbaburros.set(True)
    wait(1.0, SECONDS)  # Esperar a que baje

    # 15. Girar 45 grados a la izquierda para quedar paralelo al cargador
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 45 grados...")
    for _ in range(2):
        turn_left_pivot_55(50)  # Girar a 50% velocidad
    wait(0.5, SECONDS)  # Pausa para estabilizar
    
    # Finalizar rutina
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Autonomo completado")

def autonomous():
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("PushBack Autonomo")

    # Inicializar posiciones
    init_positions()
    
    # Ejecutar rutina autónoma
    autonomous_routine()
    
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Programa finalizado")

def user_control():
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
            brain.screen.print("Ramp:{} Tumb:{} Brush:{} {}  ".format(
                "UP" if ramp_extended else "DN",
                "UP" if tumbaburros_extended else "DN",
                ["OFF", "COL", "EJT"][brush_state],
                "UNLOAD" if unload_mode else ""
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

# create competition instance
comp = Competition(user_control, autonomous)

# actions to do when the program starts
brain.screen.clear_screen()