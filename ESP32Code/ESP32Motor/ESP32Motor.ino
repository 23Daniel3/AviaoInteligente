#include <Arduino.h>
#include <ESP32Servo.h>

// -------------------------
// CONFIGURAÇÃO DO MOTOR / ESC
// -------------------------
Servo motorEsc;
const int motorPin = 4;        // pino de sinal do ESC
int motorPulseMin = 1000;      // µs correspondendo a 0%
int motorPulseMax = 2000;      // µs correspondendo a 100%

// -------------------------
// FUNÇÕES DE CONTROLE DO MOTOR
// -------------------------

/**
 * Inicializa o ESC e envia sinal mínimo para armar com segurança
 */
void motorInit() {
  motorEsc.attach(motorPin, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(motorPulseMin); // força 0% no início
  delay(2000); // tempo típico para o ESC armar
}

/**
 * Escreve potência em % (0–100) para o motor
 */
void motorWritePercent(int pct) {
  pct = constrain(pct, 0, 100);
  int us = map(pct, 0, 100, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(us);
}

/**
 * Função de segurança: reinicia o ESC
 * Força sinal mínimo e reanexa o objeto Servo
 */
void motorReset() {
  motorEsc.detach();
  delay(100);
  motorInit();
}

// -------------------------
// FUNÇÕES UTILITÁRIAS DE CONVERSÃO
// -------------------------

/**
 * Converte µs (1000–2000) para porcentagem (0–100)
 */
int usToPercent(int us) {
  us = constrain(us, motorPulseMin, motorPulseMax);
  return map(us, motorPulseMin, motorPulseMax, 0, 100);
}

/**
 * Converte porcentagem (0–100) para µs (1000–2000)
 */
int percentToUs(int pct) {
  pct = constrain(pct, 0, 100);
  return map(pct, 0, 100, motorPulseMin, motorPulseMax);
}

// -------------------------
// SETUP / LOOP
// -------------------------
void setup() {
  Serial.begin(115200);
  motorInit(); // prepara ESC
  Serial.println("Motor pronto. Use motorWritePercent(x) para enviar potência.");
}

void loop() {}
