#include <Wire.h>
#include <SparkFun_u-blox_GNSS_Arduino_Library.h>

SFE_UBLOX_GNSS myGPS;

// Seus pinos atuais configurados
#define GPS_TX_PIN 37  // <- GPS TX
#define GPS_RX_PIN 36  // <- GPS RX
#define GPS_BAUD 9600

HardwareSerial GPSSerial(2); // Usa a UART2 do ESP32-S3

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  Serial.println("\n=== Inicializando GPS NEO-M8N (Modo Direto 9600) ===");

  // Inicia a comunicação serial direto na velocidade certa
  GPSSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_TX_PIN, GPS_RX_PIN);
  delay(200);

  // Conecta com a biblioteca u-blox
  if (myGPS.begin(GPSSerial) == false) {
    Serial.println("ERRO: GPS nao respondeu em 115200 baud.");
    Serial.println("Verifique se os fios estao bem firmes.");
    while (1) delay(100);
  }

  // Garante que o envio automático de dados (PVT) continue ativo
  myGPS.setAutoPVT(true);

  Serial.println("✓ GPS Conectado com sucesso!");
  Serial.println("Aguardando sinal dos satelites...\n");
  Serial.println("Status  | Satelites | Latitude   | Longitude   | Altitude | Velocidade");
  Serial.println("--------------------------------------------------------------------------");
}

void loop() {
  // getPVT() retorna verdadeiro a cada 10Hz (10 vezes por segundo) quando chegam dados novos
  if (myGPS.getPVT()) {
    byte fixType = myGPS.getFixType(); // 0=Sem fix, 2=2D, 3=3D
    byte numSV   = myGPS.getSIV();     // Quantidade de satélites

    if (fixType >= 2) {
      // Converte os valores brutos para unidades legíveis
      double lat   = myGPS.getLatitude() / 10000000.0;
      double lon   = myGPS.getLongitude() / 10000000.0;
      float alt    = myGPS.getAltitude() / 1000.0;       // Metros
      float speed  = myGPS.getGroundSpeed() / 1000.0;   // Metros por segundo
      float course = myGPS.getHeading() / 100000.0;     // Graus de direção

      // Alinha tudo em colunas organizadas usando Serial.printf
      Serial.printf("Fix %dD  |   %02d SV   | %.7f | %.7f | %6.1fm | %5.2f m/s (Rumo: %.1f°)\n", 
                    fixType, numSV, lat, lon, alt, speed, course);
    } else {
      // Se estiver sem sinal, mostra apenas quantos satélites ele está rastreando
      Serial.printf("Sem Fix |   %02d SV   | Procurando satelites...\n", numSV);
    }
  }
}