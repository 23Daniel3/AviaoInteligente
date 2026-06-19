#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>

constexpr uint8_t CE_PIN   = 4;
constexpr uint8_t CSN_PIN  = 5;
constexpr uint8_t SCK_PIN  = 18;
constexpr uint8_t MISO_PIN = 19;
constexpr uint8_t MOSI_PIN = 23;

RF24 radio(CE_PIN, CSN_PIN);
const uint8_t address[6] = "NODE1";

struct Packet {
    volatile uint16_t throttleUs = 1000;
};

volatile uint16_t throttleUs = 1000;

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);

    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&SPI)) {
        Serial.println("[ERRO] RF24 nao inicializou");
        while (true) delay(1000);
    }

    radio.setPALevel(RF24_PA_LOW);
    radio.setDataRate(RF24_250KBPS);
    radio.setChannel(76);
    radio.openWritingPipe(address);
    radio.stopListening();

    Serial.println("[OK] RF24 pronto — transmitindo");
}

static String lineBuffer;

void readSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            lineBuffer.trim();
            if (lineBuffer.length() > 0) {
                int v = lineBuffer.toInt();
                if (v >= 1000 && v <= 2000) {
                    throttleUs = v;
                    Serial.printf("[PC] %d\n", v);  // só ao mudar valor
                }
                lineBuffer = "";
            }
        } else {
            lineBuffer += c;
        }
    }
}

static unsigned long lastTx = 0;

void loop() {
    readSerial();  // drena TUDO do buffer a cada loop

    if (millis() - lastTx >= 20) {  // 50 Hz = 20 ms
        lastTx = millis();
        Packet pkt{throttleUs};
        bool ok = radio.write(&pkt, sizeof(pkt));
        if (!ok) Serial.println("[TX] sem ACK");
        // sem printf de sucesso aqui — causa o buffer overflow
    }
}