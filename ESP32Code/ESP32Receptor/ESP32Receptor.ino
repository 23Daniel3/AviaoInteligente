#include <Arduino.h>
#include <ESP32Servo.h>

const int channelPins[] = {17, 18, 35, 36, 37, 38};
const int numChannels = sizeof(channelPins) / sizeof(channelPins[0]);

/**
 * Inicializa pinos dos canais como entrada
 */
void channelsInit() {
  for (int i = 0; i < numChannels; i++) {
    pinMode(channelPins[i], INPUT);
  }
}

/**
 * Lê o valor PWM de um canal
 * @param channel índice (1..numChannels)
 * @return largura do pulso em microssegundos (1000–2000 us)
 */
int getChannel(int channel) {
  if (channel < 1 || channel > numChannels) return -1;
  int pin = channelPins[channel - 1];
  // pulseIn mede HIGH; timeout 25 ms (um frame típico de 20 ms)
  unsigned long us = pulseIn(pin, HIGH, 25000);
  return (int)us;
}

void setup() {
  channelsInit();
}

void loop() {}
