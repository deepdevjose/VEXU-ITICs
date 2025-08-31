// ================================================================
// VEXcode IQ – Teleoperado (4 motores + cepillo)  C++
// ---------------------------------------------------------------
// Descripción:
//   Control de un robot VEX IQ con tren motriz de 4 motores
//   y un motor adicional para el cepillo.
//
//   • Conducción tipo arcade:
//       - AxisA: avance/retroceso
//       - AxisB: giro izquierda/derecha
//   • Cepillo:
//       - ButtonFDown: gira hacia adelante (fwd)
//       - ButtonFUp:   gira hacia atrás (rev)
//
// Notas:
//   - Usa DEADZONE para evitar ruido del joystick.
//   - Se realiza clamp de velocidades a [-100, 100].
// Autor: @deepdevjose (port to C++ by ChatGPT)
// ================================================================

#include "vex.h"

using namespace vex;

// ------------- Configuración básica -------------
brain       Brain;
controller  Controller;  // Controlador primario

// ------------- Motores (ajusta puertos/polaridades) -------------
motor motorBackLeft   (PORT12, false); // Trasera izquierda
motor motorBackRight  (PORT6,  true);  // Trasera derecha (invertida)
motor motorFrontLeft  (PORT7,  false); // Delantera izquierda
motor motorFrontRight (PORT1,  true);  // Delantera derecha (invertida)

// Motor adicional (cepillo)
motor motorCepillo (PORT8, false);

// ------------- Constantes -------------
constexpr int DEADZONE = 10;   // Zona muerta joystick (0-100)

// ------------- Utilidades -------------
inline int clampPct(int v) {
  if (v > 100) return 100;
  if (v < -100) return -100;
  return v;
}

inline int applyDeadzone(int v, int dz = DEADZONE) {
  return (v >= -dz && v <= dz) ? 0 : v;
}

// ================================================================
// Funciones de Movimiento (Tren motriz)
// ================================================================
void moverAdelante(int velocidad) {
  velocidad = clampPct(velocidad);
  motorBackLeft.spin(directionType::fwd,  velocidad, velocityUnits::pct);
  motorBackRight.spin(directionType::fwd, velocidad, velocityUnits::pct);
  motorFrontLeft.spin(directionType::fwd, velocidad, velocityUnits::pct);
  motorFrontRight.spin(directionType::fwd,velocidad, velocityUnits::pct);
}

void moverAtras(int velocidad) {
  velocidad = clampPct(velocidad);
  motorBackLeft.spin(directionType::rev,  velocidad, velocityUnits::pct);
  motorBackRight.spin(directionType::rev, velocidad, velocityUnits::pct);
  motorFrontLeft.spin(directionType::rev, velocidad, velocityUnits::pct);
  motorFrontRight.spin(directionType::rev,velocidad, velocityUnits::pct);
}

void girarIzquierda(int velocidad) {
  velocidad = clampPct(velocidad);
  motorBackLeft.spin(directionType::rev,  velocidad, velocityUnits::pct);
  motorFrontLeft.spin(directionType::rev, velocidad, velocityUnits::pct);
  motorBackRight.spin(directionType::fwd, velocidad, velocityUnits::pct);
  motorFrontRight.spin(directionType::fwd,velocidad, velocityUnits::pct);
}

void girarDerecha(int velocidad) {
  velocidad = clampPct(velocidad);
  motorBackLeft.spin(directionType::fwd,  velocidad, velocityUnits::pct);
  motorFrontLeft.spin(directionType::fwd, velocidad, velocityUnits::pct);
  motorBackRight.spin(directionType::rev, velocidad, velocityUnits::pct);
  motorFrontRight.spin(directionType::rev,velocidad, velocityUnits::pct);
}

void detenerDrive(brakeType mode = brakeType::coast) {
  motorBackLeft.stop(mode);
  motorBackRight.stop(mode);
  motorFrontLeft.stop(mode);
  motorFrontRight.stop(mode);
}

// ================================================================
// Control Arcade (AxisA = avance, AxisB = giro)
// ================================================================
void controlDriveArcade() {
  // Lecturas del joystick en %
  int forward = Controller.AxisA.position(percent);
  int turn    = Controller.AxisB.position(percent);

  // Deadzone
  forward = applyDeadzone(forward);
  turn    = applyDeadzone(turn);

  // Mezcla diferencial: left = fwd + turn, right = fwd - turn
  int leftSpeed  = clampPct(forward + turn);
  int rightSpeed = clampPct(forward - turn);

  // Asignación a motores
  motorBackLeft.spin(directionType::fwd,  leftSpeed,  velocityUnits::pct);
  motorFrontLeft.spin(directionType::fwd, leftSpeed,  velocityUnits::pct);
  motorBackRight.spin(directionType::fwd, rightSpeed, velocityUnits::pct);
  motorFrontRight.spin(directionType::fwd,rightSpeed, velocityUnits::pct);

  // Opción: si ambas ruedas quedan en 0, podemos soltar a COAST
  if (leftSpeed == 0 && rightSpeed == 0) {
    detenerDrive(brakeType::coast);
  }
}

// ================================================================
// Control del Cepillo
// ================================================================
void controlarCepillo() {
  // ButtonFDown => forward; ButtonFUp => reverse
  if (Controller.ButtonFDown.pressing()) {
    motorCepillo.spin(directionType::fwd, 100, velocityUnits::pct);
  } else if (Controller.ButtonFUp.pressing()) {
    motorCepillo.spin(directionType::rev, 100, velocityUnits::pct);
  } else {
    motorCepillo.stop(brakeType::coast);
  }
}

// ================================================================
// Bucle Principal
// ================================================================
int main() {
  // Config inicial recomendada
  motorBackLeft.setBrake(brakeType::coast);
  motorBackRight.setBrake(brakeType::coast);
  motorFrontLeft.setBrake(brakeType::coast);
  motorFrontRight.setBrake(brakeType::coast);
  motorCepillo.setBrake(brakeType::coast);

  while (true) {
    controlDriveArcade();
    controlarCepillo();
    wait(20, msec); // 20 ms para estabilidad
  }
}
