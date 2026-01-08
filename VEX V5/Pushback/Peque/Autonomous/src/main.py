# ================================================================
# VEXcode – Modo Autónomo VEX chico (PushBack)
# ---------------------------------------------------------------
# Descripción:
#   Rutina autónoma simple que mueve el robot hacia la porteria mas cercana,
#   gira ligeramente, avanza un poco más y luego activa los mecanismos
#   Reutiliza la configuración de motores del código teleoperado.
#
# Autor: basado en la estructura del equipo por @deepdevjose
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
# Tren motriz (verde 18:1)    desde teleoperado
DRIVE_LEFT_PORT   = Ports.PORT11
DRIVE_RIGHT_PORT  = Ports.PORT12

# Cepillos (verde 18:1)  
BRUSH_FRONT_PORT  = Ports.PORT13
BRUSH_BOTTOM_PORT = Ports.PORT14

# Cañón (azul 6:1)
CANNON_PORT = Ports.PORT20

# tumbaburros (verde 18:1)
tumbaburros_PORT = Ports.PORT18

# Motor WAY (azul 6:1)
WAY = Ports.PORT15

# tumbaburros (verde 18:1)
tumbaburros_PORT = Ports.PORT18  

# ------------------------------------------------
# Instancias de motores y actuadores
# ------------------------------------------------
motor_left  = Motor(DRIVE_LEFT_PORT,  GearSetting.RATIO_18_1, False)
motor_right = Motor(DRIVE_RIGHT_PORT, GearSetting.RATIO_18_1, True)

brush_front  = Motor(BRUSH_FRONT_PORT,  GearSetting.RATIO_18_1, False)
brush_bottom = Motor(BRUSH_BOTTOM_PORT, GearSetting.RATIO_18_1, False)

cannon = Motor(CANNON_PORT, GearSetting.RATIO_6_1, False)
way = Motor(WAY, GearSetting.RATIO_6_1, False)

tumbaburros = Motor(tumbaburros_PORT, GearSetting.RATIO_18_1, False)

# Modos de frenado
for m in (motor_left, motor_right, brush_front, brush_bottom, cannon):
    m.set_stopping(BrakeType.COAST)
way.set_stopping(BrakeType.COAST)
tumbaburros.set_stopping(BrakeType.BRAKE)

# ================================================================
# Funciones de Movimiento Autónomo
# ================================================================
def drive_forward(velocity: int, duration: float) -> None:
    """Mueve el robot hacia adelante."""
    motor_left.spin(FORWARD, velocity, PERCENT)
    motor_right.spin(FORWARD, velocity, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()

def turn_left_degrees(degrees: float) -> None:
    """Gira el robot a la izquierda."""
    duration = degrees / 100.0
    motor_left.spin(REVERSE, 50, PERCENT)
    motor_right.spin(FORWARD, 50, PERCENT)
    wait(duration, SECONDS)
    motor_left.stop()
    motor_right.stop()


# ================================================================
# Rutina Autónoma
# ================================================================
def autonomous_routine() -> None:
    """
    Rutina autónoma:
    1. Avanza hacia adelante por 0.5 segundos
    2. Gira 35 grados a la izquierda
    3. Activa brushes, way y cannon en REVERSE para escupir pelotas
    """

    wait(5, SECONDS)  # Espera inicial antes de comenzar

    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("Iniciando autonomo...")
    
    # 1. Avanzar hacia adelante por 0.5 segundos
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando...")
    drive_forward(100, 1.06)
    brush_front.stop()
    
    # 2. Girar 30 grados a la izquierda
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Girando izquierda...")
    turn_left_degrees(33)

    # 1. Avanzar hacia adelante por 0.5 segundos
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Avanzando...")
    drive_forward(50, 0.15)

    # 3. Activar todos los motores para escupir pelotas
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Escupiendo pelotas...")
    brush_front.spin(FORWARD, 100, PERCENT)
    brush_bottom.spin(FORWARD, 100, PERCENT)
    way.spin(REVERSE, 100, PERCENT)
    cannon.spin(FORWARD, 100, PERCENT)
    wait(3.0, SECONDS)
    brush_front.stop()
    brush_bottom.stop()
    way.stop()
    cannon.stop()

    # Finalizar rutina
    brain.screen.set_cursor(2, 1)
    brain.screen.print("Autonomo completado")
    wait(1, SECONDS)

# ================================================
# Inicialización de posiciones
# ================================================
def init_positions() -> None:
    motor_left.reset_position()
    motor_right.reset_position()
    cannon.reset_position()
    way.reset_position()
    # Frenar el tumbaburros durante toda la ejecución
    tumbaburros.stop()


# ================================================================
# Programa principal
# ================================================================
def main() -> None:
    brain.screen.clear_screen()
    brain.screen.set_cursor(1, 1)
    brain.screen.print("PushBack Autonomo")

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
