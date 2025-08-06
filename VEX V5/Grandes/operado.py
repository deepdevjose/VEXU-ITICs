#region VEXcode Generated Robot Configuration
from vex import *
import urandom

# Brain should be defined by default
brain=Brain()

# Robot configuration code


# wait for rotation sensor to fully initialize
wait(30, MSEC)


# Make random actually random
def initializeRandomSeed():
    wait(100, MSEC)
    random = brain.battery.voltage(MV) + brain.battery.current(CurrentUnits.AMP) * 100 + brain.timer.system_high_res()
    urandom.seed(int(random))
      
# Set random seed 
initializeRandomSeed()


def play_vexcode_sound(sound_name):
    # Helper to make playing sounds from the V5 in VEXcode easier and
    # keeps the code cleaner by making it clear what is happening.
    print("VEXPlaySound:" + sound_name)
    wait(5, MSEC)

# add a small delay to make sure we don't print in the middle of the REPL header
wait(200, MSEC)
# clear the console to make sure we don't have the REPL in the console
print("\033[2J")

#endregion VEXcode Generated Robot Configuration
##############################################
# VEXcode Generated Robot Configuration
##############################################
from vex import *
import urandom

# Inicialización del cerebro y controlador
brain = Brain()
controller = Controller()


##############################################
# Configuración de Motores
##############################################
DEADZONE = 10  # Umbral para ignorar valores pequeños del joystick

# Motores del tren motriz
motor_back_left  = Motor(Ports.PORT12, GearSetting.RATIO_18_1, True)   # Izquierdo
motor_back_right = Motor(Ports.PORT2,  GearSetting.RATIO_18_1, False)  # Derecho
motor_front_left  = Motor(Ports.PORT1,  GearSetting.RATIO_18_1, False) # Izquierdo
motor_front_right = Motor(Ports.PORT11, GearSetting.RATIO_18_1, True)  # Derecho

# Otros motores (rampa, cepillo,  garra, pinza)
motor_rampa             = Motor(Ports.PORT10, GearSetting.RATIO_6_1,  False)
motor_cepillo           = Motor(Ports.PORT20, GearSetting.RATIO_36_1, False)
motor_garra_open_close  = Motor(Ports.PORT19, GearSetting.RATIO_36_1, False)
motor_pinza_open_close  = Motor(Ports.PORT6,  GearSetting.RATIO_36_1, False)


##############################################
# Variables Globales
##############################################
modo_rampa_auto = False
prev_ButtonB    = False

cepillo_on      = False
prev_ButtonA    = False


##############################################
# Funciones de Movimiento (Tren motriz)
##############################################
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
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(FORWARD,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(REVERSE,  velocidad, PERCENT)

def girar_derecha(velocidad):
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(REVERSE,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(FORWARD,   velocidad, PERCENT)

# Movimientos laterales (Strafe) con llantas mecanum
def girarc_izquierda(velocidad):
    # Ajusta FORWARD/REVERSE si se mueve al lado contrario
    motor_front_left.spin(REVERSE,  velocidad, PERCENT)
    motor_back_left.spin(REVERSE,   velocidad, PERCENT)
    motor_front_right.spin(FORWARD, velocidad, PERCENT)
    motor_back_right.spin(FORWARD,  velocidad, PERCENT)

def girarc_derecha(velocidad):
    # Ajusta FORWARD/REVERSE si se mueve al lado contrario
    motor_front_left.spin(FORWARD,   velocidad, PERCENT)
    motor_back_left.spin(FORWARD,    velocidad, PERCENT)
    motor_front_right.spin(REVERSE,  velocidad, PERCENT)
    motor_back_right.spin(REVERSE,   velocidad, PERCENT)

def detener():
    motor_back_left.stop()
    motor_back_right.stop()
    motor_front_left.stop()
    motor_front_right.stop()


##############################################
# Funciones de Control (Rampa, Garra, Pinza, Cepillo)
##############################################
def control_rampa_manual():
    value = controller.axis2.position()
    if abs(value) < DEADZONE:
        motor_rampa.stop()
    else:
        direction = FORWARD if value > 0 else REVERSE
        motor_rampa.spin(direction, abs(value), PERCENT)

def aplicar_rampa_auto():
    motor_rampa.set_velocity(470, RPM)
    motor_rampa.spin(FORWARD)

def toggle_rampa_mode():
    global modo_rampa_auto, prev_ButtonB
    if controller.buttonB.pressing() and not prev_ButtonB:
        modo_rampa_auto = not modo_rampa_auto
    prev_ButtonB = controller.buttonB.pressing()

def control_garra_gradual():
    if controller.buttonL1.pressing():
        motor_garra_open_close.spin(FORWARD, 60, PERCENT)
    elif controller.buttonR1.pressing():
        motor_garra_open_close.spin(REVERSE, 60, PERCENT)
    else:
        motor_garra_open_close.stop(HOLD)

def control_pinza_gradual():
    if controller.buttonL2.pressing():
        motor_pinza_open_close.spin(FORWARD, 100, PERCENT)
    elif controller.buttonR2.pressing():
        motor_pinza_open_close.spin(REVERSE, 100, PERCENT)
    else:
        motor_pinza_open_close.stop(HOLD)

def girar_cepillo():
    global cepillo_on, prev_ButtonA
    if controller.buttonA.pressing() and not prev_ButtonA:
        cepillo_on = not cepillo_on
        if cepillo_on:
            motor_cepillo.spin(REVERSE, 100, PERCENT)
        else:
            motor_cepillo.stop()
    prev_ButtonA = controller.buttonA.pressing()


##############################################
# Control Arcade con Axis3 (avance) y Axis4 (giro)
##############################################
DEADZONE = 10  # Ajusta según la sensibilidad que desees

def control_drive():
    # Leer ejes del joystick
    axis_forward = controller.axis3.position()  # Adelante / Atrás
    axis_strafe  = controller.axis4.position()  # Izquierda / Derecha (strafe)

    # Aplicar zona muerta
    if abs(axis_forward) < DEADZONE:
        axis_forward = 0
    if abs(axis_strafe) < DEADZONE:
        axis_strafe = 0

    # Si hay valor en axis_strafe, nos movemos lateralmente
    if axis_strafe > 0:
        # Strafe a la derecha
        # Equivalente a tu girarc_derecha(velocidad)
        motor_front_left.spin(FORWARD,   axis_strafe, PERCENT)
        motor_back_left.spin(REVERSE,    axis_strafe, PERCENT)
        motor_front_right.spin(REVERSE,  axis_strafe, PERCENT)
        motor_back_right.spin(FORWARD,   axis_strafe, PERCENT)

    elif axis_strafe < 0:
        # Strafe a la izquierda
        # Equivalente a tu girarc_izquierda(velocidad)
        speed = abs(axis_strafe)
        motor_front_left.spin(REVERSE,  speed, PERCENT)
        motor_back_left.spin(FORWARD,   speed, PERCENT)
        motor_front_right.spin(FORWARD, speed, PERCENT)
        motor_back_right.spin(REVERSE,  speed, PERCENT)

    # Si no hay valor en axis_strafe, vemos si hay valor en axis_forward
    elif axis_forward > 0:
        mover_adelante(axis_forward)
    elif axis_forward < 0:
        mover_atras(abs(axis_forward))

    # Si ninguno de los ejes está activo, detenemos
    else:
        detener()



##############################################
# Bucle Principal (Teleoperado)
##############################################
def main():
    while True:
        # Alternar y aplicar modo de rampa
        toggle_rampa_mode()
        if modo_rampa_auto:
            aplicar_rampa_auto()
        else:
            control_rampa_manual()
        
        # Control de cepillo, pinza y garra
        girar_cepillo()
        control_pinza_gradual()
        control_garra_gradual()

        # Control de movimiento base (Arcade con Axis3/Axis4)
        control_drive()

        # Si se presiona LEFT o RIGHT, hacemos strafe (movimiento lateral).
        if controller.buttonLeft.pressing():
            girarc_izquierda(50)
        elif controller.buttonRight.pressing():
            girarc_derecha(50)
        # Si no se presiona, seguimos con el control arcade
        
        wait(20, MSEC)  # Pequeña pausa para no saturar la CPU

# Punto de entrada
if __name__ == "__main__":
    main()
