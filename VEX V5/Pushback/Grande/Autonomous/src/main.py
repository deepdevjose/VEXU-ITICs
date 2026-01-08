# ================================================================
# VEXcode – Modo Autónomo SIMPLE con Odometría
# ---------------------------------------------------------------
# Rutina básica con métodos simples para movimiento
# Usa odometría para navegación punto a punto
#
# Hardware:
#   - Drivetrain: motores puertos 3 y 4 (36:1)
#   - Ruedas: 2.75" diámetro
#   - Inertial: puerto 6
#   - Intake: puertos 20 y 11 (6:1)
#   - Cañón: puerto 16 (18:1)
#   - Pistones: 3-wire A (descore), B (trasero)
#
# Autor: @deepdevjose
# ================================================================

from vex import *
import math

# ------------------------------------------------
# Hardware
# ------------------------------------------------
brain = Brain()
controller = Controller()

# Motores drivetrain
motor_left = Motor(Ports.PORT3, GearSetting.RATIO_36_1, True)
motor_right = Motor(Ports.PORT4, GearSetting.RATIO_36_1, False)

# Sensor inertial
imu = Inertial(Ports.PORT6)

# Mecanismos
intake = Motor(Ports.PORT20, GearSetting.RATIO_6_1, False)
intake_sup = Motor(Ports.PORT11, GearSetting.RATIO_6_1, True)
cannon = Motor(Ports.PORT16, GearSetting.RATIO_18_1, False)

# Pistones neumáticos
piston_trasero = DigitalOut(brain.three_wire_port.a)
piston_descores = DigitalOut(brain.three_wire_port.b)

# ------------------------------------------------
# PARÁMETROS
# ------------------------------------------------
WHEEL_DIAMETER = 4  # pulgadas
WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * math.pi
TRACK_WIDTH = 15  # pulgadas (distancia entre ruedas)

# Odometría
ODOM_UPDATE_MS = 10
odom = {
    "x": 0.0,
    "y": 0.0,
    "theta": 0.0,
    "last_left": 0.0,
    "last_right": 0.0,
    "running": False
}

# Tolerancias
DISTANCE_TOLERANCE = 1.5  # pulgadas
ANGLE_TOLERANCE = 3.0  # grados

# Control
KP_LINEAR = 3.5
MAX_LINEAR_SPEED = 70
KP_ANGULAR = 2.0
MAX_ANGULAR_SPEED = 50
MIN_SPEED = 10

# ------------------------------------------------
# Utilidades
# ------------------------------------------------
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

def normalize_angle(angle):
    """Normaliza ángulo a [-180, 180]"""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def heading_error_deg(target, current):
    """Calcula error angular shortest path (0-360 a [-180, 180])"""
    err = (target - current + 540) % 360 - 180
    return err

def encoder_to_inches(degrees):
    rotations = degrees / 360.0
    return rotations * WHEEL_CIRCUMFERENCE

def distance_to(x, y):
    dx = x - odom["x"]
    dy = y - odom["y"]
    return math.sqrt(dx * dx + dy * dy)

# ================================================
# CALIBRACIÓN E INICIALIZACIÓN
# ================================================
def calibrate():
    """Calibra el IMU y resetea odometría"""
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Calibrando IMU...")
    
    imu.calibrate()
    while imu.is_calibrating():
        wait(50, MSEC)
    
    motor_left.set_position(0, DEGREES)
    motor_right.set_position(0, DEGREES)
    
    odom["x"] = 0.0
    odom["y"] = 0.0
    odom["theta"] = 0.0
    odom["last_left"] = 0.0
    odom["last_right"] = 0.0
    
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Listo!")
    wait(500, MSEC)

def set_position(x=0.0, y=0.0, theta=0.0):
    """Establece posición inicial manualmente"""
    odom["x"] = x
    odom["y"] = y
    odom["theta"] = theta

# ================================================
# ODOMETRÍA (Loop en paralelo)
# ================================================
def odometry_loop():
    """Loop de odometría que actualiza posición continuamente"""
    odom["running"] = True
    
    while odom["running"]:
        # Leer encoders
        left_pos = motor_left.position(DEGREES)
        right_pos = motor_right.position(DEGREES)
        
        # Calcular deltas
        delta_left = encoder_to_inches(left_pos - odom["last_left"])
        delta_right = encoder_to_inches(right_pos - odom["last_right"])
        
        # Avance promedio
        delta_s = (delta_left + delta_right) / 2.0
        
        # Leer orientación del IMU
        theta_deg = imu.heading()
        if theta_deg > 180:
            theta_deg -= 360
        odom["theta"] = theta_deg
        
        # Actualizar posición global
        theta_rad = math.radians(theta_deg)
        odom["x"] += delta_s * math.cos(theta_rad)
        odom["y"] += delta_s * math.sin(theta_rad)
        
        # Guardar para próximo ciclo
        odom["last_left"] = left_pos
        odom["last_right"] = right_pos
        
        wait(ODOM_UPDATE_MS, MSEC)

def start_odometry():
    """Inicia el loop de odometría en paralelo"""
    Thread(odometry_loop)

def stop_odometry():
    """Detiene el loop de odometría"""
    odom["running"] = False

# ================================================
# MOVIMIENTOS BÁSICOS CON ODOMETRÍA
# ================================================
def drive_to(x, y, timeout_ms=5000):
    """Ir a un punto (x, y) usando odometría
    
    Args:
        x: coordenada X en pulgadas
        y: coordenada Y en pulgadas
        timeout_ms: tiempo máximo (default 5s)
    
    Returns:
        True si llegó, False si timeout
    """
    start_time = brain.timer.time(MSEC)
    
    while True:
        # Timeout
        if brain.timer.time(MSEC) - start_time > timeout_ms:
            motor_left.stop()
            motor_right.stop()
            return False
        
        # Verificar llegada
        dist = distance_to(x, y)
        if dist <= DISTANCE_TOLERANCE:
            motor_left.stop()
            motor_right.stop()
            return True
        
        # Calcular ángulo objetivo
        dx = x - odom["x"]
        dy = y - odom["y"]
        target_angle = math.degrees(math.atan2(dy, dx))
        angle_error = normalize_angle(target_angle - odom["theta"])
        
        # Control lineal (proporcional a distancia)
        linear = KP_LINEAR * dist
        linear = clamp(linear, -MAX_LINEAR_SPEED, MAX_LINEAR_SPEED)
        
        # Control angular (corrección de rumbo)
        angular = KP_ANGULAR * angle_error
        angular = clamp(angular, -MAX_ANGULAR_SPEED, MAX_ANGULAR_SPEED)
        
        # Mezcla arcade
        left_power = linear + angular
        right_power = linear - angular
        
        left_power = clamp(left_power, -100, 100)
        right_power = clamp(right_power, -100, 100)
        
        # Aplicar
        motor_left.spin(FORWARD, left_power, PERCENT)
        motor_right.spin(FORWARD, right_power, PERCENT)
        
        wait(20, MSEC)

def forward(inches, timeout_ms=5000):
    """Avanza recto una distancia (relativo a posición actual)"""
    theta_rad = math.radians(odom["theta"])
    target_x = odom["x"] + inches * math.cos(theta_rad)
    target_y = odom["y"] + inches * math.sin(theta_rad)
    return drive_to(target_x, target_y, timeout_ms)

def backward(inches, timeout_ms=5000):
    """Retrocede una distancia"""
    return forward(-inches, timeout_ms)

def turn_left(degrees, timeout_ms=3000):
    """Gira a la izquierda (relativo) usando IMU + encoders para precisión"""
    start_heading = imu.heading()
    start_left = motor_left.position(DEGREES)
    start_right = motor_right.position(DEGREES)
    
    settle_count = 0
    settle_required = 10  # Más ciclos para confirmar estabilidad
    
    start_time = brain.timer.time(MSEC)
    
    while settle_count < settle_required:
        # Timeout
        if brain.timer.time(MSEC) - start_time > timeout_ms:
            motor_left.stop(BRAKE)
            motor_right.stop(BRAKE)
            return False
        
        # Leer IMU - fuente principal de verdad
        current = imu.heading()
        rotation_done = heading_error_deg(current, start_heading)
        
        # Error restante basado en IMU
        err = degrees - rotation_done
        
        # Tolerancia adaptativa - muy estricta
        current_tolerance = 2.5 if abs(err) < 15 else 3.5
        
        # Verificar settling (debe estar estable)
        if abs(err) <= current_tolerance:
            settle_count += 1
            # En settling, no mover motores
            motor_left.stop(BRAKE)
            motor_right.stop(BRAKE)
            wait(20, MSEC)
            continue
        else:
            settle_count = 0
        
        # Control MUY conservador con zonas
        if abs(err) > 25:
            # Zona rápida
            turn = err * 0.3
            turn = clamp(turn, -25, 25)
        elif abs(err) > 15:
            # Zona media
            turn = err * 0.25
            turn = clamp(turn, -15, 15)
        elif abs(err) > 8:
            # Zona lenta
            turn = err * 0.2
            turn = clamp(turn, -10, 10)
        else:
            # Zona muy lenta
            turn = err * 0.15
            turn = clamp(turn, -8, 8)
        
        # Velocidad mínima solo si error es significativo
        if abs(err) > 6 and abs(turn) > 0 and abs(turn) < 5:
            turn = 5 if turn > 0 else -5
        elif abs(turn) < 3 and abs(err) > 0:
            # Muy cerca, movimientos mínimos
            turn = 3 if err > 0 else -3
        
        motor_left.spin(FORWARD, -turn, PERCENT)
        motor_right.spin(FORWARD, turn, PERCENT)
        wait(20, MSEC)
    
    # Detener con freno fuerte
    motor_left.stop(BRAKE)
    motor_right.stop(BRAKE)
    wait(100, MSEC)  # Esperar que se asiente completamente
    
    # Mostrar telemetría del giro
    final_heading = imu.heading()
    actual_rotation = heading_error_deg(final_heading, start_heading)
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Giro: {}° -> {}°    ".format(int(degrees), int(actual_rotation)))
    
    return True

def turn_right(degrees, timeout_ms=3000):
    """Gira a la derecha (relativo)"""
    return turn_left(-degrees, timeout_ms)

def turn_to_angle(target_angle, timeout_ms=3000):
    """Gira a un ángulo absoluto específico (0-360)"""
    start_heading = imu.heading()
    angle_diff = heading_error_deg(target_angle, start_heading)
    return turn_left(angle_diff, timeout_ms)

# ================================================
# CONTROL DE MECANISMOS
# ================================================
def intake_on(speed=100):
    """Enciende intake hacia adelante"""
    intake.spin(FORWARD, speed, PERCENT)
    intake_sup.spin(FORWARD, speed, PERCENT)

def intake_reverse(speed=100):
    """Enciende intake en reversa"""
    intake.spin(REVERSE, speed, PERCENT)
    intake_sup.spin(REVERSE, speed, PERCENT)

def intake_off():
    """Apaga intake"""
    intake.stop()
    intake_sup.stop()

def cannon_on(speed=100):
    """Enciende cañón"""
    cannon.spin(FORWARD, speed, PERCENT)

def cannon_reverse(speed=100):
    """Cañón en reversa"""
    cannon.spin(REVERSE, speed, PERCENT)

def cannon_off():
    """Apaga cañón"""
    cannon.stop()

def descore_open():
    """Abre pistón descore"""
    piston_descores.set(True)

def descore_close():
    """Cierra pistón descore"""
    piston_descores.set(False)

def trasero_open():
    """Abre pistón trasero (tumba burros)"""
    piston_trasero.set(True)

def trasero_close():
    """Cierra pistón trasero"""
    piston_trasero.set(False)

# ================================================
# RUTINA DE AUTÓNOMO
# ================================================
def autonomous():
    """Rutina principal de autónomo"""
    brain.screen.clear_screen()
    brain.screen.print("Autonomo Iniciando")
    
    # 1. Calibrar
    calibrate()
    
    # 2. Iniciar odometría
    start_odometry()
    
    # 3. Establecer posición inicial (opcional)
    # set_position(0, 0, 0)  # Origen en (0,0) mirando a 0°
    
    wait(500, MSEC)
    
    # ====== RUTINA DE EJEMPLO ======
    brain.screen.print("Ejecutando rutina...")
    
    # Ejemplo 1: Avanzar 20 pulgadas
    forward(20)
    wait(500, MSEC)
    
    # Ejemplo 2: Girar 15° a la izquierda
    turn_left(17)
    wait(500, MSEC)
    
    # Bajar descore después del giro
    descore_open()
    brain.screen.print("Descore ABAJO")
    wait(500, MSEC)
    
    # Ejemplo 3: Avanzar 12 pulgadas
    forward(6)
    wait(500, MSEC)
    
    # Ejemplo 4: Encender intake
    intake_on(100)
    wait(1000, MSEC)
    intake_off()

        # 9. Mover un poco atras para despegar pitillo
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Retrocediendo un poco...")
    drive_backward(10, .2)

    wait(1, SECONDS)

    # 9. Girar derecha 180 grados (106 reales)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando derecha 180...")
    turn_right_degrees(100)

    wait(1, SECONDS)

    # 11. Ir adelante para encestar
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando para encestar...")
    drive_forward(50, 0.5)
    move_ramp_to_alto()
    raise_pitillo()
    brush_bottom.stop()
    brush_front.stop()
    fire_cannon_left()
    fire_cannon_left()
    
    # Ejemplo 5: Ir a un punto específico
    # drive_to(24, 24)  # Ir a coordenadas (24, 24)
    
    # Ejemplo 6: Girar a ángulo absoluto
    # turn_to_angle(0)  # Volver a mirar hacia 0°
    
    # ====== FIN DE RUTINA ======
    
    # 4. Detener odometría
    stop_odometry()
    
    brain.screen.set_cursor(5, 1)
    brain.screen.print("COMPLETADO")

# ================================================
# PUNTO DE ENTRADA
# ================================================
if __name__ == "__main__":
    autonomous()
