#include <Arduino.h>
#include <TinyGPS++.h>

// Pinos (ajuste se necessário)
const int RX_PIN = 26; // conecta ao TX do NEO (NEO TX -> ESP RX)
const int TX_PIN = 25; // conecta ao RX do NEO (NEO RX <- ESP TX)
const unsigned long GPS_BAUD = 9600; // Baud padrão do NEO-M8N

TinyGPSPlus gps;
HardwareSerial GPSSerial(2); // UART2

unsigned long lastPrint = 0;

void setup() {
  Serial.begin(9600);
  delay(200);
  Serial.println("Iniciando GPS NEO-M8N com ESP32...");

  // Inicializa UART para o GPS (baud, config, RX, TX)
  GPSSerial.begin(GPS_BAUD, SERIAL_8N1, RX_PIN, TX_PIN);
  delay(200);
  Serial.printf("Serial GPS iniciada em %lu bps (RX:%d TX:%d)\n", GPS_BAUD, RX_PIN, TX_PIN);
}

void loop() {
  // Ler tudo do GPS e enviar para parser TinyGPSPlus
  while (GPSSerial.available()) {
    char c = (char)GPSSerial.read();
    Serial.write(c); // Mostra sentenças NMEA brutas (útil p/ debug)
    gps.encode(c);
  }

  // A cada 1s imprime dados parseados
  if (millis() - lastPrint > 1000) {
    lastPrint = millis();
    Serial.println();
    if (gps.location.isValid()) {
      Serial.print("Latitude: ");
      Serial.println(gps.location.lat(), 6);
      Serial.print("Longitude: ");
      Serial.println(gps.location.lng(), 6);
    } else {
      Serial.println("Latitude/Longitude: não disponiveis");
    }

    if (gps.altitude.isValid()) {
      Serial.print("Altitude (m): ");
      Serial.println(gps.altitude.meters());
    } else {
      Serial.println("Altitude: não disponivel");
    }

    if (gps.speed.isValid()) {
      Serial.print("Velocidade (km/h): ");
      Serial.println(gps.speed.kmph());
    } else {
      Serial.println("Velocidade: não disponivel");
    }

    if (gps.satellites.isValid()) {
      Serial.print("Satélites: ");
      Serial.println(gps.satellites.value());
    } else {
      Serial.println("Satélites: não disponivel");
    }

    if (gps.date.isValid() && gps.time.isValid()) {
      Serial.printf("Data UTC: %02d/%02d/%04d ", gps.date.day(), gps.date.month(), gps.date.year());
      Serial.printf("Hora UTC: %02d:%02d:%02d\n", gps.time.hour(), gps.time.minute(), gps.time.second());
    } else {
      Serial.println("Data/Hora: não disponivel");
    }
  }
}
