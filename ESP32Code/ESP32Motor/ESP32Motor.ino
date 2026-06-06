#include <ESP32Servo.h>

Servo esc;

void setup() {
    esc.setPeriodHertz(50);
    esc.attach(17, 1000, 2000);

    delay(1000);

    esc.writeMicroseconds(1070);
}

void loop() {
    esc.writeMicroseconds(1070);
    delay(20);
}