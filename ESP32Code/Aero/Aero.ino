#include <Arduino.h>
#include <ESC.h>

ESC meuEsc(18);

void setup() {
  Serial.begin(115200);
  
  meuEsc.begin();
}

void loop() {
  if (Serial.available()) {
    float power = Serial.parseFloat();

    meuEsc.runPower(power);

    while (Serial.available()) {
      Serial.read();
    }
  }
}