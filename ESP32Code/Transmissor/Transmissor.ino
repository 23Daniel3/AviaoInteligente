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

// ── Mesmos formatos de pacote do receptor ─────────────────────────────
struct ControlPacket {
    uint8_t  throttle;
    uint8_t  aileron;
    uint8_t  rudder;
    uint8_t  elevator;
    uint16_t timestamp;
} __attribute__((packed));

struct TelemetryPacket {
    uint16_t timestamp;
    int16_t  roll;
    int16_t  pitch;
    int16_t  yaw;
    int16_t  latDeltaM;
    int16_t  lonDeltaM;
    int16_t  altDm;
    uint8_t  speedKmh;
    uint8_t  fixType;
    uint8_t  numSV;
} __attribute__((packed));

// ── Controle recebido do PC (0-100 por canal) ─────────────────────────
volatile uint8_t ctrlThrottle = 0;
volatile uint8_t ctrlAileron  = 50;
volatile uint8_t ctrlRudder   = 50;
volatile uint8_t ctrlElevator = 50;

void setup() {
    Serial.begin(115200);

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);

    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&SPI)) {
        while (true) delay(1000); // rádio não inicializou
    }

    radio.setPALevel(RF24_PA_MAX);   // potência máxima
    radio.setDataRate(RF24_250KBPS); // mesmo data rate do receptor
    radio.setChannel(76);
    radio.enableDynamicPayloads();   // obrigatório para ACK payload
    radio.enableAckPayload();
    radio.openWritingPipe(address);
    radio.stopListening();
}

// ── Leitura do controle vindo do PC: "throttle,aileron,rudder,elevator\n" (0-100) ──
static String lineBuffer;

void readSerialControl() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            lineBuffer.trim();
            if (lineBuffer.length() > 0) {
                int v0, v1, v2, v3;
                if (sscanf(lineBuffer.c_str(), "%d,%d,%d,%d", &v0, &v1, &v2, &v3) == 4) {
                    ctrlThrottle = (uint8_t)constrain(v0, 0, 100);
                    ctrlAileron  = (uint8_t)constrain(v1, 0, 100);
                    ctrlRudder   = (uint8_t)constrain(v2, 0, 100);
                    ctrlElevator = (uint8_t)constrain(v3, 0, 100);
                }
            }
            lineBuffer = "";
        } else {
            lineBuffer += c;
        }
    }
}

static unsigned long lastTx = 0;

void loop() {
    readSerialControl(); // drena tudo do buffer a cada loop

    if (millis() - lastTx >= 20) { // 50Hz — igual ao timer de controle do dashboard
        lastTx = millis();

        ControlPacket pkt;
        pkt.throttle  = ctrlThrottle;
        pkt.aileron   = ctrlAileron;
        pkt.rudder    = ctrlRudder;
        pkt.elevator  = ctrlElevator;
        pkt.timestamp = (uint16_t)(millis() & 0xFFFF);

        bool ok = radio.write(&pkt, sizeof(pkt));

        if (ok && radio.isAckPayloadAvailable()) {
            TelemetryPacket tp;
            radio.read(&tp, sizeof(tp));

            uint16_t nowMs = (uint16_t)(millis() & 0xFFFF);
            uint16_t rtt   = nowMs - tp.timestamp; // wraparound natural em uint16

            // ── Tradução de volta para valores reais — só acontece aqui ──
            float roll  = tp.roll  / 100.0f;
            float pitch = tp.pitch / 100.0f;
            float yaw   = tp.yaw   / 100.0f;
            float altM  = tp.altDm / 10.0f;

            Serial.printf("%.2f,%.2f,%.2f,%d,%d,%.1f,%u,%u,%u,%u\n",
                          roll, pitch, yaw,
                          tp.latDeltaM, tp.lonDeltaM, altM,
                          tp.speedKmh, tp.fixType, tp.numSV, rtt);
        }
    }
}
