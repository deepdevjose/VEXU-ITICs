#region VEXcode Generated Robot Configuration
from vex import *
import urandom

# Brain should be defined by default
brain=Brain()

# Robot configuration code
brain_inertial = Inertial()



# generating and setting random seed
def initializeRandomSeed():
    wait(100, MSEC)
    xaxis = brain_inertial.acceleration(XAXIS) * 1000
    yaxis = brain_inertial.acceleration(YAXIS) * 1000
    zaxis = brain_inertial.acceleration(ZAXIS) * 1000
    systemTime = brain.timer.system() * 100
    urandom.seed(int(xaxis + yaxis + zaxis + systemTime)) 
    
# Initialize random seed 
initializeRandomSeed()

#endregion VEXcode Generated Robot Configuration
#region VEX IQ Robot Configuration
from vex import *
import urandom

brain = Brain()
controller = Controller()

# Motores tren motriz
motor_back_left  = Motor(Ports.PORT12, False)  # Trasera izquierda
motor_back_right = Motor(Ports.PORT6, True)    # Trasera derecha
motor_front_left = Motor(Ports.PORT7, False)   # Delantera izquierda
motor_front_right= Motor(Ports.PORT1, True)    # Delantera derecha

# Motor adicional (cepillo)
motor_cepillo = Motor(Ports.PORT8, False)

DEADZONE = 10

# Inicializar semilla aleatoria
def initializeRandomSeed():
    wait(100, MSEC)
    random = brain.battery.voltage(MV) + brain.battery.current(CurrentUnits.AMP) * 100 + brain.timer.system_high_res()
    urandom.seed(int(random))

initializeRandomSeed()

# Movimiento básico
def mover_adelante(velocidad):
    motor_back_left.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def mover_atras(velocidad):
    motor_back_left.spin(REVERSE, velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def girar_izquierda(velocidad):
    motor_back_left.spin(REVERSE, velocidad, PERCENT)
    motor_front_left.spin(REVERSE, velocidad, PERCENT)
    motor_back_right.spin(FORWARD, velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)

def girar_derecha(velocidad):
    motor_back_left.spin(FORWARD, velocidad, PERCENT)
    motor_front_left.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(REVERSE, velocidad, PERCENT)
    motor_front_right.spin(REVERSE, velocidad, PERCENT)

def detener():
    motor_back_left.stop()
    motor_back_right.stop()
    motor_front_left.stop()
    motor_front_right.stop()

# Control Arcade con Axis3 y Axis4
def control_drive():
    forward = controller.axisA.position()
    turn = controller.axisB.position()

    if abs(forward) < DEADZONE: forward = 0
    if abs(turn) < DEADZONE: turn = 0

    left_speed = forward + turn
    right_speed = forward - turn

    motor_back_left.spin(FORWARD, left_speed, PERCENT)
    motor_front_left.spin(FORWARD, left_speed, PERCENT)
    motor_back_right.spin(FORWARD, right_speed, PERCENT)
    motor_front_right.spin(FORWARD, right_speed, PERCENT)

# Control motor cepillo
def controlar_cepillo():
    if controller.buttonFDown.pressing():
        motor_cepillo.spin(FORWARD, 100, PERCENT)
    elif controller.buttonFUp.pressing():
        motor_cepillo.spin(REVERSE, 100, PERCENT)
    else:
        motor_cepillo.stop()

# Main loop
def main():
    while True:
        control_drive()
        controlar_cepillo()
        wait(20, MSEC)

if __name__ == "__main__":
    main()
