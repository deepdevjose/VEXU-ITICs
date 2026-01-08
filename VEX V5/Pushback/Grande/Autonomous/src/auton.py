# ================================================================
# VEXcode – Modo Autónomo con Odometría 2D
# ---------------------------------------------------------------
# Sistema completo de odometría y control go-to-point:
#   ✓ Odometría 2D (x, y, θ) con Inertial + encoders
#   ✓ Loop de odometría en paralelo (10ms)
#   ✓ Control go-to-point con PID
#   ✓ drive_to(x, y) con tolerancias
#   ✓ Sistema de waypoints
#   ✓ Telemetría en tiempo real
#
# Hardware:
#   - Drivetrain: tank, 1 motor por lado (puertos 5 y 4)
#   - Ruedas: omni verdes (2.75" diámetro)
#   - Inertial: puerto 3, montado centrado apuntando al frente
#   - Encoders: integrados en motores
#
# Autor: @deepdevjose
# ================================================================

from vex import *
import math

# ------------------------------------------------
# Hardware (importado de main.py)
# ------------------------------------------------
brain = Brain()
controller = Controller()

# Motores
DRIVE_LEFT_PORT = Ports.PORT3
DRIVE_RIGHT_PORT = Ports.PORT4
motor_left = Motor(DRIVE_LEFT_PORT, GearSetting.RATIO_36_1, True)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_36_1, False)

# Inertial (puerto 3)
INERTIAL_PORT = Ports.PORT3
imu = Inertial(INERTIAL_PORT)

# ------------------------------------------------
# PARÁMETROS DE TUNING (ajustar en campo)
# ------------------------------------------------
# Geometría del robot
WHEEL_DIAMETER_INCHES = 4.0  # Ruedas de 4 pulgadas
WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER_INCHES * math.pi
TRACK_WIDTH_INCHES = 10.5  # Distancia entre ruedas (medir!)

# Loop de odometría
ODOM_UPDATE_MS = 10  # Actualización cada 10ms (100Hz)

# Tolerancias para "llegada"
TARGET_DISTANCE_TOLERANCE = 1.5  # pulgadas
TARGET_ANGLE_TOLERANCE = 3.0     # grados

# Ganancias PID para movimiento (CALIBRAR EN CAMPO)
# Movimiento lineal (avance)
KP_LINEAR = 3.5      # Proporcional: más alto = más agresivo
KD_LINEAR = 0.5      # Derivativo: suaviza oscilaciones
MAX_LINEAR_SPEED = 70  # % velocidad máxima lineal

# Control angular (giro)
KP_ANGULAR = 2.0     # Proporcional para corrección de ángulo
KD_ANGULAR = 0.3     # Derivativo para giro
MAX_ANGULAR_SPEED = 50  # % velocidad máxima de giro

# Velocidad mínima (evita zona muerta)
MIN_DRIVE_SPEED = 10  # %

# Timeout de seguridad
DRIVE_TO_TIMEOUT_MS = 5000  # 5 segundos máximo por punto

# ------------------------------------------------
# Variables de estado de odometría
# ------------------------------------------------
odom = {
    "x": 0.0,           # Posición X en pulgadas
    "y": 0.0,           # Posición Y en pulgadas
    "theta": 0.0,       # Orientación en grados
    "last_left": 0.0,   # Último encoder izquierdo
    "last_right": 0.0,  # Último encoder derecho
    "running": False    # Flag de loop activo
}

# Variables de control
control = {
    "target_x": 0.0,
    "target_y": 0.0,
    "last_error_linear": 0.0,
    "last_error_angular": 0.0,
    "arrived": False
}

# ------------------------------------------------
# Utilidades matemáticas
# ------------------------------------------------
def clamp(value, min_val, max_val):
    """Limita valor entre min y max."""
    return max(min_val, min(max_val, value))

def normalize_angle(angle):
    """Normaliza ángulo a rango [-180, 180]."""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def degrees_to_radians(deg):
    """Convierte grados a radianes."""
    return deg * math.pi / 180.0

def distance_between_points(x1, y1, x2, y2):
    """Calcula distancia euclidiana entre dos puntos."""
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

def angle_to_point(x1, y1, x2, y2):
    """Calcula ángulo (en grados) desde (x1,y1) hacia (x2,y2).
    0° = hacia la derecha (+X)
    90° = hacia arriba (+Y)
    """
    dx = x2 - x1
    dy = y2 - y1
    return math.degrees(math.atan2(dy, dx))

def encoder_to_inches(encoder_degrees):
    """Convierte grados del encoder a pulgadas recorridas."""
    rotations = encoder_degrees / 360.0
    return rotations * WHEEL_CIRCUMFERENCE

# ================================================================
# CALIBRACIÓN E INICIALIZACIÓN
# ================================================================
def calibrate_sensors():
    """Calibra el Inertial y resetea encoders.
    SIEMPRE llamar al inicio del autónomo.
    """
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Calibrando IMU...")
    
    # Calibrar Inertial (tarda ~2 segundos)
    imu.calibrate()
    while imu.is_calibrating():
        wait(50, MSEC)
    
    brain.screen.set_cursor(2, 1)
    brain.screen.print("IMU OK")
    
    # Resetear encoders
    motor_left.set_position(0, DEGREES)
    motor_right.set_position(0, DEGREES)
    
    # Inicializar odometría en origen
    odom["x"] = 0.0
    odom["y"] = 0.0
    odom["theta"] = imu.heading()  # Usar orientación actual como referencia
    odom["last_left"] = 0.0
    odom["last_right"] = 0.0
    
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Odom inicializada")
    wait(500, MSEC)

def set_origin(x=0.0, y=0.0, theta=None):
    """Establece el origen de la odometría manualmente.
    Útil si conoces tu posición inicial en el campo.
    """
    odom["x"] = x
    odom["y"] = y
    if theta is not None:
        odom["theta"] = theta
    else:
        odom["theta"] = imu.heading()

# ================================================================
# LOOP DE ODOMETRÍA (corre en paralelo)
# ================================================================
def odometry_loop():
    """Loop de odometría que actualiza (x, y, θ) continuamente.
    Debe correr en un thread separado durante todo el autónomo.
    
    Algoritmo:
    1. Lee encoders → calcula ΔL, ΔR
    2. Calcula avance local ΔS = (ΔL + ΔR) / 2
    3. Lee θ del IMU (absoluto)
    4. Proyecta: x += ΔS·cos(θ), y += ΔS·sin(θ)
    """
    odom["running"] = True
    
    while odom["running"]:
        # 1) Leer encoders actuales
        left_pos = motor_left.position(DEGREES)
        right_pos = motor_right.position(DEGREES)
        
        # 2) Calcular deltas
        delta_left = left_pos - odom["last_left"]
        delta_right = right_pos - odom["last_right"]
        
        # Convertir a pulgadas
        delta_left_inches = encoder_to_inches(delta_left)
        delta_right_inches = encoder_to_inches(delta_right)
        
        # 3) Avance local (asumimos tank sin lateral)
        delta_s = (delta_left_inches + delta_right_inches) / 2.0
        
        # 4) Leer orientación absoluta del IMU
        theta_deg = imu.heading()  # 0-360°
        # Convertir a -180 a 180 para cálculos
        if theta_deg > 180:
            theta_deg -= 360
        odom["theta"] = theta_deg
        
        # 5) Proyectar a coordenadas globales
        theta_rad = degrees_to_radians(theta_deg)
        odom["x"] += delta_s * math.cos(theta_rad)
        odom["y"] += delta_s * math.sin(theta_rad)
        
        # 6) Guardar para próximo ciclo
        odom["last_left"] = left_pos
        odom["last_right"] = right_pos
        
        # Esperar antes del siguiente ciclo
        wait(ODOM_UPDATE_MS, MSEC)

def start_odometry():
    """Inicia el loop de odometría en paralelo."""
    # En VEXcode Python, usamos Thread
    from threading import Thread
    odom_thread = Thread(target=odometry_loop)
    odom_thread.start()

def stop_odometry():
    """Detiene el loop de odometría."""
    odom["running"] = False

# ================================================================
# CONTROL GO-TO-POINT
# ================================================================
def compute_drive_output(target_x, target_y):
    """Calcula comandos de motores para ir hacia (target_x, target_y).
    
    Retorna: (left_power, right_power) en porcentaje [-100, 100]
    
    Algoritmo:
    1. Calcula error de distancia
    2. Calcula error angular
    3. PID lineal → avance
    4. PID angular → giro
    5. Mezcla: left = avance - giro, right = avance + giro
    """
    # 1) Error de posición
    dx = target_x - odom["x"]
    dy = target_y - odom["y"]
    distance_error = math.sqrt(dx * dx + dy * dy)
    
    # 2) Error angular
    target_angle = math.degrees(math.atan2(dy, dx))
    angle_error = normalize_angle(target_angle - odom["theta"])
    
    # 3) Control lineal (PD)
    linear_output = KP_LINEAR * distance_error
    linear_derivative = KD_LINEAR * (distance_error - control["last_error_linear"])
    linear_speed = linear_output + linear_derivative
    linear_speed = clamp(linear_speed, -MAX_LINEAR_SPEED, MAX_LINEAR_SPEED)
    
    # 4) Control angular (PD)
    angular_output = KP_ANGULAR * angle_error
    angular_derivative = KD_ANGULAR * (angle_error - control["last_error_angular"])
    angular_speed = angular_output + angular_derivative
    angular_speed = clamp(angular_speed, -MAX_ANGULAR_SPEED, MAX_ANGULAR_SPEED)
    
    # 5) Mezcla arcade
    left_power = linear_speed - angular_speed
    right_power = linear_speed + angular_speed
    
    # Clamp final
    left_power = clamp(left_power, -100, 100)
    right_power = clamp(right_power, -100, 100)
    
    # Aplicar velocidad mínima (evita zona muerta)
    if abs(left_power) > 0 and abs(left_power) < MIN_DRIVE_SPEED:
        left_power = MIN_DRIVE_SPEED if left_power > 0 else -MIN_DRIVE_SPEED
    if abs(right_power) > 0 and abs(right_power) < MIN_DRIVE_SPEED:
        right_power = MIN_DRIVE_SPEED if right_power > 0 else -MIN_DRIVE_SPEED
    
    # Guardar errores para derivada
    control["last_error_linear"] = distance_error
    control["last_error_angular"] = angle_error
    
    return left_power, right_power, distance_error, angle_error

def check_arrival(target_x, target_y):
    """Verifica si el robot llegó al objetivo dentro de tolerancias.
    
    Retorna: True si llegó, False si no
    """
    distance = distance_between_points(odom["x"], odom["y"], target_x, target_y)
    # Opcional: también chequear ángulo si es crítico
    return distance <= TARGET_DISTANCE_TOLERANCE

# ================================================================
# COMANDOS DE MOVIMIENTO
# ================================================================
def drive_to(x, y, timeout_ms=None):
    """Mueve el robot al punto (x, y) usando odometría.
    
    Bloquea hasta llegar o timeout.
    
    Args:
        x: coordenada X objetivo (pulgadas)
        y: coordenada Y objetivo (pulgadas)
        timeout_ms: tiempo máximo de espera (None = usar default)
    
    Returns:
        True si llegó, False si timeout
    """
    if timeout_ms is None:
        timeout_ms = DRIVE_TO_TIMEOUT_MS
    
    control["target_x"] = x
    control["target_y"] = y
    control["last_error_linear"] = 0.0
    control["last_error_angular"] = 0.0
    control["arrived"] = False
    
    start_time = brain.timer.time(MSEC)
    
    brain.screen.set_cursor(1, 1)
    brain.screen.print("-> ({:.1f}, {:.1f})  ".format(x, y))
    
    while True:
        elapsed = brain.timer.time(MSEC) - start_time
        
        # Timeout
        if elapsed > timeout_ms:
            motor_left.stop()
            motor_right.stop()
            brain.screen.set_cursor(4, 1)
            brain.screen.print("TIMEOUT!           ")
            return False
        
        # Verificar llegada
        if check_arrival(x, y):
            motor_left.stop()
            motor_right.stop()
            control["arrived"] = True
            brain.screen.set_cursor(4, 1)
            brain.screen.print("ARRIVED!           ")
            return True
        
        # Compute control
        left_pwr, right_pwr, dist_err, ang_err = compute_drive_output(x, y)
        
        # Aplicar motores
        if left_pwr == 0:
            motor_left.stop()
        else:
            motor_left.spin(FORWARD, left_pwr, PERCENT)
        
        if right_pwr == 0:
            motor_right.stop()
        else:
            motor_right.spin(FORWARD, right_pwr, PERCENT)
        
        # Telemetría
        brain.screen.set_cursor(2, 1)
        brain.screen.print("Pos: ({:.1f},{:.1f})  ".format(odom["x"], odom["y"]))
        brain.screen.set_cursor(3, 1)
        brain.screen.print("Err: d={:.1f} a={:.1f}  ".format(dist_err, ang_err))
        
        wait(20, MSEC)

def turn_to_angle(target_angle_deg, timeout_ms=3000):
    """Gira el robot a un ángulo absoluto específico.
    
    Args:
        target_angle_deg: ángulo objetivo en grados
        timeout_ms: tiempo máximo
    
    Returns:
        True si llegó, False si timeout
    """
    start_time = brain.timer.time(MSEC)
    
    while True:
        elapsed = brain.timer.time(MSEC) - start_time
        
        if elapsed > timeout_ms:
            motor_left.stop()
            motor_right.stop()
            return False
        
        # Error angular
        angle_error = normalize_angle(target_angle_deg - odom["theta"])
        
        if abs(angle_error) <= TARGET_ANGLE_TOLERANCE:
            motor_left.stop()
            motor_right.stop()
            return True
        
        # Control proporcional simple
        turn_speed = KP_ANGULAR * angle_error
        turn_speed = clamp(turn_speed, -MAX_ANGULAR_SPEED, MAX_ANGULAR_SPEED)
        
        motor_left.spin(FORWARD, -turn_speed, PERCENT)
        motor_right.spin(FORWARD, turn_speed, PERCENT)
        
        wait(20, MSEC)

def drive_forward_distance(distance_inches, timeout_ms=5000):
    """Avanza una distancia recta (relativo a posición actual).
    
    Args:
        distance_inches: distancia a avanzar (+ = adelante, - = atrás)
        timeout_ms: tiempo máximo
    """
    # Calcular punto objetivo en dirección actual
    theta_rad = degrees_to_radians(odom["theta"])
    target_x = odom["x"] + distance_inches * math.cos(theta_rad)
    target_y = odom["y"] + distance_inches * math.sin(theta_rad)
    
    return drive_to(target_x, target_y, timeout_ms)

# ================================================================
# RUTINAS DE AUTÓNOMO
# ================================================================
def autonomous_skills():
    """Rutina de autonomous skills (1 minuto).
    Ejemplo: cuadrado de 24" x 24"
    """
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("SKILLS AUTON")
    
    # Calibrar antes de empezar
    calibrate_sensors()
    start_odometry()
    
    wait(500, MSEC)
    
    # Ejemplo: cuadrado
    brain.screen.print("Cuadrado 24x24")
    drive_to(24, 0)
    wait(500, MSEC)
    
    drive_to(24, 24)
    wait(500, MSEC)
    
    drive_to(0, 24)
    wait(500, MSEC)
    
    drive_to(0, 0)
    wait(500, MSEC)
    
    # Detener odometría
    stop_odometry()
    
    brain.screen.set_cursor(5, 1)
    brain.screen.print("COMPLETADO")

def autonomous_match_red():
    """Rutina de match (15s) - lado rojo."""
    brain.screen.clear_screen()
    brain.screen.print("RED AUTON")
    
    calibrate_sensors()
    start_odometry()
    
    # TODO: Implementar rutina específica del match
    # Ejemplo:
    # drive_to(12, 0)
    # turn_to_angle(90)
    # drive_forward_distance(18)
    
    wait(1000, MSEC)
    stop_odometry()

def autonomous_match_blue():
    """Rutina de match (15s) - lado azul."""
    brain.screen.clear_screen()
    brain.screen.print("BLUE AUTON")
    
    calibrate_sensors()
    start_odometry()
    
    # TODO: Implementar rutina específica del match
    
    wait(1000, MSEC)
    stop_odometry()

def test_odometry():
    """Rutina de prueba: solo muestra odometría sin moverse.
    Útil para verificar que los cálculos son correctos.
    """
    brain.screen.clear_screen()
    brain.screen.print("TEST ODOMETRY")
    
    calibrate_sensors()
    start_odometry()
    
    # Solo mostrar posición durante 30 segundos
    start = brain.timer.time(MSEC)
    while brain.timer.time(MSEC) - start < 30000:
        brain.screen.set_cursor(2, 1)
        brain.screen.print("X: {:.2f} in     ".format(odom["x"]))
        brain.screen.set_cursor(3, 1)
        brain.screen.print("Y: {:.2f} in     ".format(odom["y"]))
        brain.screen.set_cursor(4, 1)
        brain.screen.print("Theta: {:.1f} deg  ".format(odom["theta"]))
        
        wait(100, MSEC)
    
    stop_odometry()

def test_drive_straight():
    """Prueba simple: avanza 43 pulgadas en línea recta."""
    brain.screen.clear_screen()
    brain.screen.print("Avanzar 43 pulgadas")
    
    calibrate_sensors()
    start_odometry()
    
    wait(500, MSEC)
    
    # Avanzar 43 pulgadas hacia adelante
    drive_forward_distance(43)
    
    wait(1000, MSEC)
    
    # Mostrar posición final
    brain.screen.set_cursor(5, 1)
    brain.screen.print("Final: ({:.1f},{:.1f})".format(odom["x"], odom["y"]))
    
    stop_odometry()

# ================================================================
# PUNTO DE ENTRADA
# ================================================================
def autonomous():
    """Punto de entrada del autónomo.
    Selecciona qué rutina correr (por ahora skills).
    """
    # Cambiar esta línea para seleccionar rutina:
    test_drive_straight()
    # autonomous_skills()
    # autonomous_match_red()
    # autonomous_match_blue()
    # test_odometry()

if __name__ == "__main__":
    # Para pruebas individuales
    autonomous()
