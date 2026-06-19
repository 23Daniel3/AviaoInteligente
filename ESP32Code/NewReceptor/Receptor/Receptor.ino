#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>

constexpr uint8_t CE_PIN   = 4;
constexpr uint8_t CSN_PIN  = 5;
constexpr uint8_t SCK_PIN  = 16;
constexpr uint8_t MISO_PIN = 17;
constexpr uint8_t MOSI_PIN = 6;

SPIClass radioSPI(FSPI);
RF24 radio(CE_PIN, CSN_PIN);
const uint8_t address[6] = "NODE1";

struct Packet {
    uint32_t counter;
};

Packet packet;

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);

    radioSPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&radioSPI)) {
        Serial.println("[ERRO] RF24 nao inicializou");
        while (true) delay(1000);
    }

    radio.setPALevel(RF24_PA_LOW);
    radio.setDataRate(RF24_250KBPS);
    radio.setChannel(76);
    radio.openReadingPipe(1, address);
    radio.startListening();

    Serial.println("[OK] RF24 pronto — escutando");
}

void loop() {
    if (radio.available()) {
        while (radio.available()) {
            radio.read(&packet, sizeof(packet));
        }
        Serial.printf("[RX] Recebido counter=%lu\n", packet.counter);
    }
}