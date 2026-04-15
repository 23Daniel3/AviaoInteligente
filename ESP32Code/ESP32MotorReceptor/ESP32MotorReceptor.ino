#include <Arduino.h>
#include <ESP32Servo.h>

// -------------------------
// CONFIGURAÇÃO DE PINOS
// -------------------------
const int channelPins[] = {17, 18, 35, 36, 37, 38}; // pinos onde o receptor está ligado (CH1..CH6)
const int numChannels = sizeof(channelPins) / sizeof(channelPins[0]);

Servo motorEsc;
const int motorPin = 4; // pino de sinal para ESC (NÃO use um pino do channelPins)

// -------------------------
// PARÂMETROS DO ESC / MOTOR
// -------------------------
int motorPulseMin = 1000; // microsegundos correspondendo a 0% (test: 1000)
int motorPulseMax = 2000; // microsegundos correspondendo a 100% (test: 2000)

const int motorRampStepMs = 20; // delay entre incrementos ao aplicar percent
const int motorRampStepPct = 2; // passo em % (rampa)

// -------------------------
// FUNÇÕES: leitura dos canais
// -------------------------
/**
 * Inicializa pinos dos canais como entrada
 */
void channelsInit() {
  for (int i = 0; i < numChannels; i++) {
    pinMode(channelPins[i], INPUT);
  }
}

/**
 * Lê largura do pulso em microssegundos (1000..2000)
 * @param channel índice (1..numChannels)
 * @return largura em µs ou -1 se timeout
 */
int getChannelUs(int channel) {
  if (channel < 1 || channel > numChannels) return -1;
  int pin = channelPins[channel - 1];
  // pulseIn bloqueia até o pulso; timeout de 30 ms
  unsigned long us = pulseIn(pin, HIGH, 30000);
  if (us == 0) return -1;
  return (int)us;
}

/**
 * Converte us (1000..2000) para porcentagem (0..100)
 */
int usToPercent(int us) {
  // Se os pulsos do receptor saírem fora de 1000..2000, limita
  us = constrain(us, 800, 2200);
  return map(us, 1000, 2000, 0, 100);
}

// -------------------------
// FUNÇÕES: controle do motor
// -------------------------
/**
 * Inicializa ESC no pino definido e mantém em mínimo por segurança
 */
void motorInit() {
  motorEsc.attach(motorPin, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(motorPulseMin); // sinal mínimo
  Serial.println("Motor ESC anexado; enviando pulso mínimo por 2000 ms para armar.");
  delay(2000); // mantém pulso mínimo para armar ESC
}

/**
 * Envia microsegundos diretamente para o ESC
 */
void motorWriteMicro(int us) {
  us = constrain(us, motorPulseMin - 100, motorPulseMax + 100);
  motorEsc.writeMicroseconds(us);
}

/**
 * Envia porcentagem 0..100 para o ESC (mapeia para microsegundos)
 */
void motorWritePercent(int pct) {
  pct = constrain(pct, 0, 100);
  int us = map(pct, 0, 100, motorPulseMin, motorPulseMax);
  motorEsc.writeMicroseconds(us);
}

/**
 * Faz rampa suave até targetPct
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
 * Calibração do ESC: usuária envia 'c' via Serial e segue instruções.
 * Padrão: ligar stick no máximo, ligar ESC (bipes), depois mover para mínimo.
 */
void motorCalibrateSequence() {
  Serial.println("Iniciando sequência de calibração do ESC:");
  Serial.println("1) Coloque o throttle (CH3) no MÁXIMO e pressione ENTER.");
  while (!Serial.available()) delay(10);
  Serial.read(); // consome
  Serial.println("Agora, conecte a bateria ao ESC. Aguarde os bipes. Depois pressione ENTER e mova throttle para MINIMO.");
  while (!Serial.available()) delay(10);
  Serial.read();
  // envia max e depois min
  motorWriteMicro(motorPulseMax);
  delay(2000);
  motorWriteMicro(motorPulseMin);
  delay(2000);
  Serial.println("Calibração: comandos MAX e MIN enviados.");
}

/**
 * Retorna true se sinal do canal 3 parece válido
 */
bool hasValidThrottleSignal(int ch3_us) {
  return (ch3_us >= 900 && ch3_us <= 2200);
}

// -------------------------
// SETUP / LOOP
// -------------------------
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("=== Inicializando sistema ESC + Leitura de canais ===");
  channelsInit();
  motorInit();
  Serial.println("Setup completo. Digite 'c' + ENTER para calibrar ESC manualmente.");
}

/**
 * Loop principal:
 * - lê CH3 (throttle);
 * - converte para %;
 * - escreve para ESC (rampa leve);
 * - imprime debug constantemente.
 */
void loop() {
  // processa comando serial simples
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'c' || cmd == 'C') {
      motorCalibrateSequence();
    }
  }

  int ch3_us = getChannelUs(3); // leitura do canal 3
  if (ch3_us > 0 && hasValidThrottleSignal(ch3_us)) {
    int throttlePct = usToPercent(ch3_us);
    // aplica comando diretamente (ou use motorRampToPercent para suavizar)
    motorWritePercent(throttlePct);

    Serial.print("CH3_us: ");
    Serial.print(ch3_us);
    Serial.print(" us  -> ");
    Serial.print(throttlePct);
    Serial.println(" %");
  } else {
    // Sem sinal confiável: manda 0% (segurança)
    motorWritePercent(0);
    Serial.print("Sem sinal CH3 válido (");
    Serial.print(ch3_us);
    Serial.println("). Motor mantido em 0%.");
  }

  delay(40); // ~25 Hz de atualização
}
