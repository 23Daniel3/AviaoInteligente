#include <Arduino.h>
#include <ESP32Servo.h>

Servo leftAileronServo;
Servo rightAileronServo;
Servo leftFlapServo;
Servo rightFlapServo;
Servo lemeServo;
Servo profundorServo;

int pinLeftAileronServo = 4;
int pinRightAileronServo = 5;
int pinLeftFlapServo = 6;
int pinRightFlapServo = 7;
int pinLemeServo = 15;
int pinProfundorServo = 16;

void setup() {
  const int pulseMin = 400;
  const int pulseMax = 2600;

  leftAileronServo.attach(pinLeftAileronServo, pulseMin, pulseMax);
  rightAileronServo.attach(pinRightAileronServo, pulseMin, pulseMax);
  leftFlapServo.attach(pinLeftFlapServo, pulseMin, pulseMax);
  rightFlapServo.attach(pinRightFlapServo, pulseMin, pulseMax);
  lemeServo.attach(pinLemeServo, pulseMin, pulseMax);
  profundorServo.attach(pinProfundorServo, pulseMin, pulseMax);
}

void loop() {}


void leftAileron(int degrees) {
  leftAileronServo.write(degrees);
}

void rightAileron(int degrees) {
  rightAileronServo.write(degrees);
}

void leftFlap(int degrees) {
  leftFlapServo.write(degrees);
}

void rightFlap(int degrees) {
  rightFlapServo.write(degrees);
}

void leme(int degrees) {
  lemeServo.write(degrees);
}

void profundor(int degrees) {
  profundorServo.write(degrees);
}
