# ================================================================
# VEXcode – Modo Autónomo VEX Grande (PushBack)
# ---------------------------------------------------------------
# Descripción:
#   Reutiliza la configuración de motores del código teleoperado.
#
# Autor: @deepdevjose
# ================================================================

from vex import *
import time

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
WAY_PORT = Ports.PORT16

# Sensor óptico
OPTICAL_SENSOR_PORT = Ports.PORT19

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

# Rangos de colores para sensor óptico estos estan en HUE
COLOR_RED_MIN = 3
COLOR_RED_MAX = 17
COLOR_BLUE_MIN = 148
COLOR_BLUE_MAX = 215

# ------------------------------------------------
# Parametros de odometria 2D
# ------------------------------------------------
# Medidas de las llantas para odometría, estas las medi a mano con un flexometro
WHEEL_DIAMETER_CM = 10.0       # Diámetro de la llanta: 10cm
WHEEL_TRAVEL_CM = 33.5         # 1 vuelta completa = 33.5cm recorridos
WHEEL_DEGREES = 364.0          # 1 vuelta completa = 285 grados en encoder, uno pensaria que siempre sera 360 grados.

# Conversión: grados por centímetro
DEGREES_PER_CM = WHEEL_DEGREES / WHEEL_TRAVEL_CM  # 285/64 = 4.453125 grados/cm

# ------------------------------------------------
# Instancias de motores
# ------------------------------------------------
# Drivetrain: reversed en constructor según montaje físico
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_36_1, False)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_36_1, True)


# Cannon/WAY: ajustar reversed para que FORWARD=disparar, REVERSE=unjam
# Si el comportamiento no coincide, invertir aquí en vez de en el código
intake = Motor(INTAKE_PORT, GearSetting.RATIO_6_1, False)
intake_sup = Motor(INTAKE_SUP_PORT, GearSetting.RATIO_6_1, True)

cannon = Motor(CANNON_PORT, GearSetting.RATIO_18_1, False)

# Pistones neumáticos
piston_trasero = DigitalOut(brain.three_wire_port.a)
piston_descores = DigitalOut(brain.three_wire_port.b)

# Sensor óptico, este detecta tambien colores ademas de parametros de distancia como cerca, lejos etc.
optical_sensor = Optical(OPTICAL_SENSOR_PORT)

# Variable global para selección de equipo, asi me evito hacer dos codigos, solo hago una desicion.
# True = Equipo Rojo, False = Equipo Azul
team_is_red = True

# Modos de frenado
for m in (motor_left, motor_right, intake, intake_sup, cannon):
    m.set_stopping(DRIVE_BRAKE_MODE)

# ================================================================
# Funciones de Detección de Colores
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
    """Verifica si hay un objeto cerca usando proximidad del sensor."""
    # Proximity devuelve un valor 0-100%, consideramos 'near' > 50%
    return optical_sensor.is_near_object()

def select_team() -> None:
    """
    Permite seleccionar el equipo al inicio del programa usando el controlador.
    Presiona ButtonUp (arriba) para Rojo, ButtonDown (abajo) para Azul.
    """
    global team_is_red
    
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("=== SELECTOR DE EQUIPO ===")
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Controller UP: ROJO")
    brain.screen.set_cursor(4, 1)
    brain.screen.print("Controller DOWN: AZUL")
    brain.screen.set_cursor(6, 1)
    brain.screen.print("Esperando seleccion...")
    
    # Esperar hasta que presionen un botón del controlador
    while True:
        if controller.buttonUp.pressing():
            team_is_red = True
            brain.screen.set_cursor(8, 1)
            brain.screen.print(">>> EQUIPO ROJO <<<")
            controller.screen.clear_screen()
            controller.screen.set_cursor(1, 1)
            controller.screen.print("EQUIPO: ROJO")
            wait(1, SECONDS)
            break
        elif controller.buttonDown.pressing():
            team_is_red = False
            brain.screen.set_cursor(8, 1)
            brain.screen.print(">>> EQUIPO AZUL <<<")
            controller.screen.clear_screen()
            controller.screen.set_cursor(1, 1)
            controller.screen.print("EQUIPO: AZUL")
            wait(1, SECONDS)
            break
        wait(0.1, SECONDS)

# ================================================================
# Funciones de Movimiento Autónomo con Odometría
# ================================================================
def drive_distance_cm(distance_cm: float, velocity: int = 50) -> None:
    """
    Mueve el robot una distancia específica en centímetros usando odometría.
    
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
    
    # Mover ambos motores la distancia calculada
    motor_left.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, False)
    motor_right.spin_for(direction, degrees_abs, DEGREES, velocity, PERCENT, True)

def drive_forward(velocity: int, duration: float) -> None:
    """Mueve el robot hacia adelante por tiempo (legacy)."""
    motor_left.spin(FORWARD, velocity, PERCENT)
    motor_right.spin(FORWARD, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def drive_backward(velocity: int, duration: float) -> None:
    """Mueve el robot hacia atrás por tiempo (legacy)."""
    motor_left.spin(REVERSE, velocity, PERCENT)
    motor_right.spin(REVERSE, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_left_degrees(degrees: float, velocity: int) -> None:
    """Gira el robot a la izquierda."""
    duration = degrees / 100.0
    motor_left.spin(REVERSE, velocity, PERCENT)
    motor_right.spin(FORWARD, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_right_degrees(degrees: float, velocity: int) -> None:
    """Gira el robot a la derecha."""
    duration = abs(degrees) / 100.0
    motor_left.spin(FORWARD, velocity, PERCENT)
    motor_right.spin(REVERSE, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_left_pivot_90(velocity: int = 50) -> None:
    """
    Gira 90 grados a la izquierda pivotando sobre la llanta izquierda.
    La llanta izquierda permanece frenada mientras la derecha avanza 25cm.
    Luego la izquierda retrocede 5cm mientras la derecha está frenada.
    """
    # Distancia que debe recorrer la llanta derecha para girar 90 grados
    pivot_distance_cm = 20.0
    degrees_to_turn = pivot_distance_cm * DEGREES_PER_CM  # 50 * 4.453125 = 222.65625 grados
    
    # PASO 1: Resetear encoder de la llanta derecha para empezar en 0
    motor_right.reset_position()
    
    # PASO 2: Frenar la llanta izquierda (aplicar brake como pivote)
    motor_left.stop(BrakeType.BRAKE)
    
    # PASO 3: Mover solo la llanta derecha hacia adelante
    motor_right.spin_for(FORWARD, degrees_to_turn, DEGREES, velocity, PERCENT, True)
    
    # PASO 4: Frenar la llanta derecha y preparar la izquierda
    motor_right.stop(BrakeType.BRAKE)
    motor_left.reset_position()
    
    # PASO 5: Retroceder la llanta izquierda 5cm mientras la derecha está frenada
    # Como motor_left tiene reversed=True, usamos FORWARD para retroceder físicamente
    back_distance_cm = 15.5
    back_degrees = back_distance_cm * DEGREES_PER_CM
    motor_left.spin_for(REVERSE, back_degrees, DEGREES, velocity, PERCENT)
    
    # PASO 6: Frenar ambas llantas al terminar
    motor_left.stop(BrakeType.BRAKE)
    motor_right.stop(BrakeType.BRAKE)


# ================================================================
# Rutina Autónoma
# ================================================================
def autonomous_routine() -> None:
    """
    Rutina autónoma:
    1. Avanza 118cm hacia adelante con odometría
    2. Gira 90 grados a la izquierda pivotando sobre la llanta izquierda
    """

    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Iniciando autonomo...")
    
    # 1. Avanzar 118cm hacia adelante usando odometría y activar pistón de descores
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 118cm...")
    drive_distance_cm(49, 50)  # 118cm a 50% velocidad
    piston_descores.set(True)  # Activar pistón de descorers
    wait(0.1, SECONDS)  # Pausa para estabilizar

    # 2. Girar 90 grados a la izquierda (pivote sobre llanta izquierda)
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando 90 grados...")
    turn_left_pivot_90(70)  # Girar a 60% velocidad
    wait(0.2, SECONDS)  # Pausa para estabilizar

    # 3. Avanzar otros 40cm hacia adelante usando odometría
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando 40cm...")
    drive_distance_cm(23, 100)  # 40cm a 100% velocidad
    wait(0.2, SECONDS)  # Pausa para estabilizar

    # 4. Activar motores y hacer movimiento de sacudida para recoger pelotas
    brain.screen.set_cursor(2, 1)
    brain.screen.print("recogiendo pelotas...")
    
    # 4.1 Activar intake, intake_sup y cannon en Forward para recoger pelotas del cargador
    intake.spin(FORWARD, 80, PERCENT)
    intake_sup.spin(FORWARD, 80, PERCENT)
    cannon.spin(FORWARD, 40, PERCENT)
    wait(0.2, SECONDS)  # Pausa para estabilizar

    # 4.2 y 4.3 Hacer movimientos de sacudida hasta detectar objeto near
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Cargando pelotas...")
    
    # LED del sensor apagado durante la carga
    optical_sensor.set_light_power(0, PERCENT)
    
    # Repetir movimiento de sacudida hasta detectar objeto near
    max_iterations = 20  # Máximo 20 ciclos (~8 segundos) para evitar bucle infinito
    iteration_count = 0
    
    while not is_object_near() and iteration_count < max_iterations:
        # Sacudida hacia adelante (corta y rápida)
        motor_left.spin(FORWARD, 60, PERCENT)
        motor_right.spin(FORWARD, 60, PERCENT)
        wait(0.2, SECONDS)
        
        # Sacudida hacia atrás (corta y rápida)
        motor_left.spin(REVERSE, 60, PERCENT)
        motor_right.spin(REVERSE, 60, PERCENT)
        wait(0.2, SECONDS)
        
        iteration_count += 1
    
    # 4.3 Detener motores de intake/cannon y drive train
    brain.screen.set_cursor(2, 1)
    if is_object_near():
        brain.screen.print("Carga completa!")
        wait(.2, SECONDS)  # Esperar 1 segundo más después de detectar near
    else:
        brain.screen.print("Tiempo de carga terminado")
    
    intake.stop()
    intake_sup.stop()
    cannon.stop()
    motor_left.stop()
    motor_right.stop()
    wait(0.2, SECONDS)  # Pausa para estabilizar

    #5. Girar 10 grados para alinear con la portería
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Alineando con porteria...")
    turn_right_degrees(15, 50)  # Girar 10 grados a la derecha a 50% velocidad
    wait(0.2, SECONDS)  # Pausa para estabilizar

    
    #6. Ir atrás 70 cm para despegar de la portería y ensestar
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Retrocediendo 90cm...")
    drive_distance_cm(-50, 60)  # -80cm a 50% velocidad
    wait(0.2, SECONDS)  # Pausa para estabilizar

    motor_left.stop(HOLD)
    motor_right.stop(HOLD)

    #7. Ensestar: activar intake, intake_sup y cannon con filtrado de colores
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Ensestando...")
    
    # Activar LED del sensor óptico al 100% durante el paso 7
    optical_sensor.set_light_power(100, PERCENT)
    
    # Tiempo total de ensestado (en ciclos de 0.1 segundos)
    max_cycles = 30  # 3 segundos total
    cycle_count = 0
    enemy_detected = False
    
    while cycle_count < max_cycles and not enemy_detected:
        # Si somos equipo rojo
        if team_is_red:
            # Detectar si hay pelota azul (color enemigo)
            if is_blue_detected():
                # DETENER intakes inmediatamente
                intake.stop()
                intake_sup.stop()
                brain.screen.set_cursor(3, 1)
                brain.screen.print("Pelota azul bloqueada!")
                # Esperar 0.3 segundos para que cannon termine de empujar pelota amiga
                wait(0.3, SECONDS)
                cannon.stop()
                enemy_detected = True  # Marcar para salir del bucle
            else:
                # Continuar normalmente (dejar pasar rojas)
                intake.spin(FORWARD, 80, PERCENT)
                intake_sup.spin(FORWARD, 80, PERCENT)
                cannon.spin(REVERSE, 100, PERCENT)
        else:
            # Si somos equipo azul (lógica inversa)
            if is_red_detected():
                # DETENER intakes inmediatamente
                intake.stop()
                intake_sup.stop()
                brain.screen.set_cursor(3, 1)
                brain.screen.print("Pelota roja bloqueada!")
                # Esperar 0.3 segundos para que cannon termine de empujar pelota amiga
                wait(0.3, SECONDS)
                cannon.stop()
                enemy_detected = True  # Marcar para salir del bucle
            else:
                # Continuar normalmente (dejar pasar azules)
                intake.spin(FORWARD, 80, PERCENT)
                intake_sup.spin(FORWARD, 80, PERCENT)
                cannon.spin(REVERSE, 100, PERCENT)
        
        wait(0.1, SECONDS)
        cycle_count += 1
    
    # Detener todos los motores y apagar LED
    intake.stop()
    intake_sup.stop()
    cannon.stop()
    optical_sensor.set_light_power(0, PERCENT)

    # Finalizar rutina
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Autonomo completado")

# ================================================
# Inicialización de posiciones
# ================================================
def init_positions() -> None:
    motor_left.reset_position()
    motor_right.reset_position()
    cannon.reset_position()
    intake.reset_position()
    intake_sup.reset_position()
    # Pistones en posición inicial
    piston_trasero.set(False)
    piston_descores.set(False)


# ================================================================
# Programa principal
# ================================================================
def main() -> None:
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("PushBack Autonomo")

    # Selector de equipo
    select_team()
    
    # Inicializar posiciones
    init_positions()
    
    # Ejecutar rutina autónoma
    autonomous_routine()
    
    brain.screen.set_cursor(3, 1)
    brain.screen.print("Programa finalizado")

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
if __name__ == "__main__":
    main()
