/*
  Teste isolado do BNO080 via SPI no ESP32S3
  Objetivo: confirmar comunicação e ler giroscópio + orientação (rotation vector)
  
  Ligações (ajuste conforme sua fiação real):
  SCK    -> GPIO12
  MOSI   -> GPIO11
  MISO   -> GPIO13
  CSN    -> GPIO10
  INT    -> GPIO9
  RSTN   -> GPIO8
  PS0/WAK-> GPIO7
  PS1    -> 3.3V (fixo, fora do código)
*/

#include <SparkFun_BNO080_Arduino_Library.h>
#include <SPI.h>

BNO080 myIMU;

// Pinos do barramento SPI (ESP32S3 permite remapear)
#define PIN_SCK  17
#define PIN_MISO  16
#define PIN_MOSI  15
#define BNO080_CS   7
#define BNO080_INT  6
#define BNO080_RST  5
#define BNO080_PS0  4
// Pino PS1 Vai conectado ao 3.3;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(1000);

  Serial.println("=== Teste BNO080 via SPI ===");

  // Remapeia os pinos do SPI antes do begin()
  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, BNO080_CS);

  if (myIMU.beginSPI(BNO080_CS, BNO080_PS0, BNO080_INT, BNO080_RST) == false) {
    Serial.println("ERRO: BNO080 não respondeu via SPI.");
    Serial.println("Verifique: fiação, PS1=HIGH, alimentação 3.3V, INT conectado.");
    while (1) delay(100);
  }

  Serial.println("BNO080 conectado com sucesso!");

  // Habilita relatórios (taxa em ms)
  myIMU.enableGyro(20);            // giroscópio puro, 50Hz
  myIMU.enableRotationVector(20);  // orientação fundida (roll/pitch/yaw), 50Hz

  Serial.println("Relatórios habilitados. Iniciando leitura...");
  Serial.println("gyroX,gyroY,gyroZ,roll,pitch,yaw");
}

void loop() {
  if (myIMU.dataAvailable()) {
    float gx = myIMU.getGyroX();
    float gy = myIMU.getGyroY();
    float gz = myIMU.getGyroZ();

    float roll  = myIMU.getRoll()  * 180.0 / PI;
    float pitch = myIMU.getPitch() * 180.0 / PI;
    float yaw   = myIMU.getYaw()   * 180.0 / PI;

    // Imprime no formato CSV pra facilitar visualizar/plotar depois
    // Serial.print(gx, 4); Serial.print(",");
    // Serial.print(gy, 4); Serial.print(",");
    // Serial.print(gz, 4); Serial.print(",");
    Serial.print(roll, 2); Serial.print(",");
    Serial.print(pitch, 2); Serial.print(",");
    Serial.println(yaw, 2);
  }
}
