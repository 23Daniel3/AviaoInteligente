#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>
#include "driver/gpio.h"
#include "esp_timer.h"
#include <Wire.h>
#include <math.h>
#include <SparkFun_BNO080_Arduino_Library.h>
#include <SparkFun_u-blox_GNSS_Arduino_Library.h>

// ── Pinos ────────────────────────────────────────────────────────────
constexpr gpio_num_t ESC_GPIO            = GPIO_NUM_38;
constexpr gpio_num_t SERVO_AILERON_GPIO  = GPIO_NUM_1;   // Aileron   ← LeftX
constexpr gpio_num_t SERVO_RUDDER_GPIO   = GPIO_NUM_2;   // Leme      ← RightX
constexpr gpio_num_t SERVO_ELEVATOR_GPIO = GPIO_NUM_42;  // Profundor ← RightY

constexpr uint8_t CE_PIN   = 46;
constexpr uint8_t CSN_PIN  = 9;
constexpr uint8_t SCK_PIN  = 10;
constexpr uint8_t MOSI_PIN = 11;
constexpr uint8_t MISO_PIN = 12;

// IMU — barramento SPI próprio, separado do rádio
#define PIN_SCK     17
#define PIN_MISO    16
#define PIN_MOSI    15
#define BNO080_CS   7
#define BNO080_INT  6
#define BNO080_RST  5
#define BNO080_PS0  4
// PS1 vai direto no 3.3V (fixo, fora do código)

// GPS — mantido exatamente como já validado (9600 baud)
#define GPS_TX_PIN 37  // <- GPS TX
#define GPS_RX_PIN 36  // <- GPS RX
#define GPS_BAUD 9600

// ── Limites PWM ───────────────────────────────────────────────────────
constexpr int PWM_MIN       = 1000;
constexpr int PWM_MAX       = 2000;
constexpr int PWM_MIN_SERVO = 500;
constexpr int PWM_MAX_SERVO = 2500;
constexpr int SERVO_MID     = 1500;

const uint8_t address[6] = "NODE1";

// ════════════════════════════════════════════════════════
// PACOTES DE RÁDIO — formato comprimido
// ════════════════════════════════════════════════════════

// Uplink: transmissor → receptor (controle, 0-100 por canal)
struct ControlPacket {
    uint8_t  throttle;   // 0-100
    uint8_t  aileron;    // 0-100 (50 = centro)
    uint8_t  rudder;     // 0-100 (50 = centro)
    uint8_t  elevator;   // 0-100 (50 = centro)
    uint16_t timestamp;  // millis() truncado, usado para RTT/latência
} __attribute__((packed));
// 6 bytes

// Downlink: receptor → transmissor, devolvido como ACK payload
struct TelemetryPacket {
    uint16_t timestamp;   // eco do timestamp recebido (RTT)
    int16_t  roll;        // graus * 100
    int16_t  pitch;       // graus * 100
    int16_t  yaw;         // graus * 100
    int16_t  latDeltaM;   // metros ao norte do home
    int16_t  lonDeltaM;   // metros ao leste do home
    int16_t  altDm;       // altitude em decímetros
    uint8_t  speedKmh;
    uint8_t  fixType;     // 0=sem fix, 2=2D, 3=3D
    uint8_t  numSV;       // satélites em uso
} __attribute__((packed));
// 17 bytes — ainda sobra bastante espaço dos 32 disponíveis

// ── STRUCT SERVO ───────────────────────────────────────
struct ServoTimer {
    gpio_num_t         pin;
    volatile int       pulseUs;
    esp_timer_handle_t periodTimer;
    esp_timer_handle_t pulseTimer;
};

static ServoTimer servos[3]; // [0]=aileron  [1]=leme  [2]=profundor

BNO080 myIMU;
SFE_UBLOX_GNSS myGPS;
HardwareSerial GPSSerial(2); // UART2 do ESP32-S3

// ── Telemetria compartilhada entre cores (protegida por spinlock) ────
struct TelemetrySnapshot {
    int16_t roll  = 0;
    int16_t pitch = 0;
    int16_t yaw   = 0;
    int16_t latDeltaM = 0;
    int16_t lonDeltaM = 0;
    int16_t altDm     = 0;
    uint8_t speedKmh  = 0;
    uint8_t fixType   = 0;
    uint8_t numSV     = 0;
};

static TelemetrySnapshot telemetrySnap;
static portMUX_TYPE telemetryMux = portMUX_INITIALIZER_UNLOCKED;

static TelemetrySnapshot telemetryGet() {
    TelemetrySnapshot copy;
    portENTER_CRITICAL(&telemetryMux);
    copy = telemetrySnap;
    portEXIT_CRITICAL(&telemetryMux);
    return copy;
}

// ════════════════════════════════════════════════════════
// ESC — esp_timer, inalterado
// ════════════════════════════════════════════════════════
volatile int      escPulseUs    = PWM_MIN;

esp_timer_handle_t periodTimer = nullptr;
esp_timer_handle_t pulseTimer  = nullptr;

void pulseEndCallback(void*) {
    gpio_set_level(ESC_GPIO, 0);
}

void periodCallback(void*) {
    gpio_set_level(ESC_GPIO, 1);
    esp_timer_start_once(pulseTimer, escPulseUs);
}

void escSetup() {
    gpio_config_t cfg = {};
    cfg.mode         = GPIO_MODE_OUTPUT;
    cfg.pin_bit_mask = (1ULL << ESC_GPIO);
    gpio_config(&cfg);
    gpio_set_level(ESC_GPIO, 0);

    esp_timer_create_args_t pulseArgs = {};
    pulseArgs.callback        = pulseEndCallback;
    pulseArgs.name            = "esc_pulse";
    pulseArgs.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&pulseArgs, &pulseTimer);

    esp_timer_create_args_t periodArgs = {};
    periodArgs.callback        = periodCallback;
    periodArgs.name            = "esc_period";
    periodArgs.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&periodArgs, &periodTimer);
    esp_timer_start_periodic(periodTimer, 20000);
}

void escWrite(int us) {
    escPulseUs = constrain(us, PWM_MIN, PWM_MAX);
}

// ════════════════════════════════════════════════════════
// SERVOS — esp_timer, inalterado
// ════════════════════════════════════════════════════════
void servoPulseEndCb(void* arg) {
    ServoTimer* s = (ServoTimer*)arg;
    gpio_set_level(s->pin, 0);
}

void servoPeriodCb(void* arg) {
    ServoTimer* s = (ServoTimer*)arg;
    gpio_set_level(s->pin, 1);
    esp_timer_start_once(s->pulseTimer, s->pulseUs);
}

void servoSetup(ServoTimer& s, gpio_num_t pin, int initialUs,
                const char* namePulse, const char* namePeriod) {
    s.pin     = pin;
    s.pulseUs = initialUs;

    gpio_config_t cfg = {};
    cfg.mode         = GPIO_MODE_OUTPUT;
    cfg.pin_bit_mask = (1ULL << pin);
    gpio_config(&cfg);
    gpio_set_level(pin, 0);

    esp_timer_create_args_t pulseArgs = {};
    pulseArgs.callback        = servoPulseEndCb;
    pulseArgs.arg             = &s;
    pulseArgs.name            = namePulse;
    pulseArgs.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&pulseArgs, &s.pulseTimer);

    esp_timer_create_args_t periodArgs = {};
    periodArgs.callback        = servoPeriodCb;
    periodArgs.arg             = &s;
    periodArgs.name            = namePeriod;
    periodArgs.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&periodArgs, &s.periodTimer);
    esp_timer_start_periodic(s.periodTimer, 20000);
}

void servoWrite(ServoTimer& s, int us) {
    s.pulseUs = constrain(us, PWM_MIN_SERVO, PWM_MAX_SERVO);
}

// ── Tradução 0-100 → PWM (feita aqui, no receptor) ────────────────────
static inline int mapMotor0to100ToPwm(uint8_t v) {
    if (v > 100) v = 100;
    return PWM_MIN + (int)((v / 100.0f) * (PWM_MAX - PWM_MIN));
}

static inline int mapServo0to100ToPwm(uint8_t v) {
    if (v > 100) v = 100;
    return PWM_MIN_SERVO + (int)((v / 100.0f) * (PWM_MAX_SERVO - PWM_MIN_SERVO));
}

// ── Valores globais recebidos via rádio (já em PWM) ───────────────────
volatile int motorValue   = PWM_MIN;
volatile int aileronValue = SERVO_MID;
volatile int rudderValue  = SERVO_MID;
volatile int elevValue    = SERVO_MID;

// ════════════════════════════════════════════════════════
// IMU
// ════════════════════════════════════════════════════════
void imuSetup() {
    SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, BNO080_CS);

    if (myIMU.beginSPI(BNO080_CS, BNO080_PS0, BNO080_INT, BNO080_RST) == false) {
        while (true) delay(100); // sensor não respondeu — trava em modo seguro
    }

    myIMU.enableGyro(20);            // 50Hz
    myIMU.enableRotationVector(20);  // roll/pitch/yaw fundidos, 50Hz
}

void imuUpdateTelemetry() {
    if (myIMU.dataAvailable()) {
        float roll  = myIMU.getRoll()  * 180.0f / PI;
        float pitch = myIMU.getPitch() * 180.0f / PI;
        float yaw   = myIMU.getYaw()   * 180.0f / PI;

        portENTER_CRITICAL(&telemetryMux);
        telemetrySnap.roll  = (int16_t)(roll  * 100.0f);
        telemetrySnap.pitch = (int16_t)(pitch * 100.0f);
        telemetrySnap.yaw   = (int16_t)(yaw   * 100.0f);
        portEXIT_CRITICAL(&telemetryMux);
    }
}

// ════════════════════════════════════════════════════════
// GPS
// ════════════════════════════════════════════════════════
static bool   homeIsSet = false;
static double homeLat   = 0.0;
static double homeLon   = 0.0;
constexpr double DEG_TO_M = 111320.0; // aproximação válida para áreas pequenas

void gpsSetup() {
    // 1. Inicia a comunicação na velocidade padrão de fábrica (9600)
    GPSSerial.begin(9600, SERIAL_8N1, GPS_TX_PIN, GPS_RX_PIN);
    delay(500);

    if (myGPS.begin(GPSSerial) == false) {
        while (true) delay(100); // GPS não respondeu — trava em modo seguro
    }

    // 2. Comando para o módulo u-blox mudar a velocidade interna dele para 38400
    myGPS.setSerialRate(38400);
    delay(100);

    // 3. Reinicia a UART do ESP32 para acompanhar a nova velocidade do GPS
    GPSSerial.begin(38400, SERIAL_8N1, GPS_TX_PIN, GPS_RX_PIN);
    delay(200);

    // 4. Configura a frequência de atualização (Taxa de Navegação)
    // Recomendo 5 Hz (5 vezes por segundo) para os módulos NEO-M8N comuns.
    // Se o seu módulo for um u-blox original mais moderno (ex: M9N), pode tentar 10.
    myGPS.setNavigationFrequency(5); 

    // 5. Ativa o auto-envio dos dados de posição, velocidade e tempo reunidos
    myGPS.setAutoPVT(true);
}

void gpsUpdateTelemetry() {
    if (!myGPS.getPVT()) return;

    byte fixType = myGPS.getFixType();
    byte numSV   = myGPS.getSIV();

    int16_t latDeltaM = 0, lonDeltaM = 0, altDm = 0;
    uint8_t speedKmh  = 0;

    if (fixType >= 3) {
        double lat   = myGPS.getLatitude()  / 10000000.0;
        double lon   = myGPS.getLongitude() / 10000000.0;
        float  alt   = myGPS.getAltitude()  / 1000.0f;     // m
        float  speed = myGPS.getGroundSpeed() / 1000.0f;   // m/s

        if (!homeIsSet) {
            homeLat   = lat;
            homeLon   = lon;
            homeIsSet = true;
        }

        double deltaNorte = (lat - homeLat) * DEG_TO_M;
        double deltaLeste = (lon - homeLon) * DEG_TO_M * cos(homeLat * PI / 180.0);

        deltaNorte = constrain(deltaNorte, -32760.0, 32760.0);
        deltaLeste = constrain(deltaLeste, -32760.0, 32760.0);

        latDeltaM = (int16_t)lround(deltaNorte);
        lonDeltaM = (int16_t)lround(deltaLeste);
        altDm     = (int16_t)lround(alt * 10.0f);
        speedKmh  = (uint8_t)constrain((int)lround(speed * 3.6f), 0, 255);
    }

    portENTER_CRITICAL(&telemetryMux);
    telemetrySnap.latDeltaM = latDeltaM;
    telemetrySnap.lonDeltaM = lonDeltaM;
    telemetrySnap.altDm     = altDm;
    telemetrySnap.speedKmh  = speedKmh;
    telemetrySnap.fixType   = fixType;
    telemetrySnap.numSV     = numSV;
    portEXIT_CRITICAL(&telemetryMux);
}

// ═══════════════════════════════════════════════════════
// TASK DO RÁDIO — 100% no Core 0, SPI próprio (HSPI),
// separado do SPI da IMU
// ═══════════════════════════════════════════════════════
void radioTask(void* param) {
    SPIClass spi(HSPI);
    RF24 radio(CE_PIN, CSN_PIN);

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);
    spi.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&spi)) {
        while (true) vTaskDelay(pdMS_TO_TICKS(1000)); // rádio não inicializou
    }

    radio.setPALevel(RF24_PA_MAX);     // potência máxima, conforme pedido
    radio.setDataRate(RF24_250KBPS);   // melhor sensibilidade/alcance
    radio.setChannel(76);
    radio.enableDynamicPayloads();     // obrigatório para ACK payload
    radio.enableAckPayload();
    radio.openReadingPipe(1, address);
    radio.startListening();
    radio.flush_rx();

    // Pré-carrega um ACK vazio para o primeiro pacote que chegar
    TelemetryPacket initial = {};
    radio.writeAckPayload(1, &initial, sizeof(initial));

    ControlPacket pkt;

    for (;;) {
        if (radio.available()) {
            while (radio.available()) {
                radio.read(&pkt, sizeof(pkt)); // mantém só o pacote mais recente
            }

            motorValue   = mapMotor0to100ToPwm(pkt.throttle);
            aileronValue = mapServo0to100ToPwm(pkt.aileron);
            rudderValue  = mapServo0to100ToPwm(pkt.rudder);
            elevValue    = mapServo0to100ToPwm(pkt.elevator);

            // Monta a telemetria comprimida com o snapshot mais recente
            TelemetrySnapshot snap = telemetryGet();
            TelemetryPacket tp;
            tp.timestamp = pkt.timestamp; // eco — usado pro transmissor calcular RTT
            tp.roll       = snap.roll;
            tp.pitch      = snap.pitch;
            tp.yaw        = snap.yaw;
            tp.latDeltaM  = snap.latDeltaM;
            tp.lonDeltaM  = snap.lonDeltaM;
            tp.altDm      = snap.altDm;
            tp.speedKmh   = snap.speedKmh;
            tp.fixType    = snap.fixType;
            tp.numSV      = snap.numSV;

            // Será devolvido automaticamente no ACK do PRÓXIMO pacote recebido
            radio.writeAckPayload(1, &tp, sizeof(tp));
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// ═══════════════════════════════════════════════════════
// SETUP — Core 1
// ═══════════════════════════════════════════════════════
void setup() {
    escSetup();
    escWrite(PWM_MIN);

    servoSetup(servos[0], SERVO_AILERON_GPIO,  SERVO_MID, "srv0_pulse", "srv0_period");
    servoSetup(servos[1], SERVO_RUDDER_GPIO,   SERVO_MID, "srv1_pulse", "srv1_period");
    servoSetup(servos[2], SERVO_ELEVATOR_GPIO, SERVO_MID, "srv2_pulse", "srv2_period");

    delay(200);
    escWrite(PWM_MIN);
    delay(5000); // tempo de boot do ESC (bips de confirmação)

    // RF24 isolado no Core 0 — Wire/SPI da IMU só é acessado do Core 1
    xTaskCreatePinnedToCore(radioTask, "Radio", 10000, NULL, 1, NULL, 0);

    imuSetup();
    gpsSetup();
}

// ═══════════════════════════════════════════════════════
// LOOP — Core 1: ESC + Servos + IMU + GPS
// ═══════════════════════════════════════════════════════
void loop() {
    escWrite(motorValue);
    servoWrite(servos[0], aileronValue);
    servoWrite(servos[1], rudderValue);
    servoWrite(servos[2], elevValue);

    imuUpdateTelemetry();
    gpsUpdateTelemetry();
}
