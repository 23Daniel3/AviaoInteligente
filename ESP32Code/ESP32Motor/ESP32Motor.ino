#include <Arduino.h>
#include <ESP32Servo.h>

Servo motorEsc;
const int motorPin = 18;

// valores calibrados do ESC
int motorPulseMin = 1190; // microsegundos no 0%
int motorPulseMax = 1672; // microsegundos no 100%

// parâmetros de rampa
const int motorRampStepMs = 50; // tempo entre passos
const int motorRampStepPct = 1; // passo em %

/**
 * Inicializa o ESC/motor no pino definido
 */
void motorInit() {
  motorEsc.attach(motorPin, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(motorPulseMin); // sempre arma em 0%
  delay(1500);
}

/**
 * Envia comando direto em microsegundos
 * @param us largura de pulso em microsegundos
 */
void motorWriteMicro(int us) {
  us = constrain(us, motorPulseMin - 200, motorPulseMax + 200);
  motorEsc.writeMicroseconds(us);
}

/**
 * Envia comando em porcentagem (0–100%)
 * @param pct valor percentual de potência
 */
void motorWritePercent(int pct) {
  pct = constrain(pct, 0, 100);
  int us = map(pct, 0, 100, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(us);
}

/**
 * Faz rampa suave até o valor percentual alvo
 * @param targetPct destino em %
 */
void motorRampToPercent(int targetPct) {
  int currentUs = motorEsc.readMicroseconds();
  if (currentUs == 0) currentUs = motorPulseMin;
  int currentPct = map(constrain(currentUs, motorPulseMin, motorPulseMax),
                       motorPulseMin, motorPulseMax, 0, 100);

  targetPct = constrain(targetPct, 0, 100);

  if (targetPct > currentPct) {
    for (int p = currentPct; p <= targetPct; p += motorRampStepPct) {
      motorWritePercent(p);
      delay(motorRampStepMs);
    }
  } else {
    for (int p = currentPct; p >= targetPct; p -= motorRampStepPct) {
      motorWritePercent(p);
      delay(motorRampStepMs);
    }
  }
  motorWritePercent(targetPct);
}

/**
 * Rotina de calibração do ESC
 * Envia max e depois min para ensinar limites
 */
void motorCalibrate() {
  // passo 1: max throttle
  motorEsc.writeMicroseconds(motorPulseMax);
  delay(2000);

  // passo 2: min throttle
  motorEsc.writeMicroseconds(motorPulseMin);
  delay(2000);
}

/**
 * Retorna último valor de microsegundos enviado
 */
int motorReadMicro() {
  return motorEsc.readMicroseconds();
}

/**
 * Retorna último valor em %
 */
int motorReadPercent() {
  int us = motorEsc.readMicroseconds();
  return map(constrain(us, motorPulseMin, motorPulseMax),
             motorPulseMin, motorPulseMax, 0, 100);
}

void setup() {
  motorInit();
}

void loop() {
  // exemplo de uso:
  // motorWritePercent(30);
  // motorRampToPercent(70);
  // motorCalibrate();
}
