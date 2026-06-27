#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>
#include "driver/gpio.h"
#include "esp_timer.h"
#include <Wire.h>
#include <SparkFun_BNO080_Arduino_Library.h>
#include <SparkFun_u-blox_GNSS_Arduino_Library.h>

// ── Pinos ────────────────────────────────────────────────────────────
constexpr gpio_num_t ESC_GPIO            = GPIO_NUM_38;
constexpr gpio_num_t SERVO_AILERON_GPIO  = GPIO_NUM_1;  // Aileron   ← LeftX
constexpr gpio_num_t SERVO_RUDDER_GPIO   = GPIO_NUM_2;  // Leme      ← RightX
constexpr gpio_num_t SERVO_ELEVATOR_GPIO = GPIO_NUM_42;  // Profundor ← RightY

constexpr uint8_t CE_PIN   = 46;
constexpr uint8_t CSN_PIN  = 9;
constexpr uint8_t SCK_PIN  = 10;
constexpr uint8_t MOSI_PIN = 11;
constexpr uint8_t MISO_PIN = 12;

// IMU
// Pinos do barramento SPI (ESP32S3 permite remapear)
#define PIN_SCK  17
#define PIN_MISO  16
#define PIN_MOSI  15
#define BNO080_CS   7
#define BNO080_INT  6
#define BNO080_RST  5
#define BNO080_PS0  4
// Pino PS1 Vai conectado ao 3.3;

// GPS
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

// ── STRUCT SERVO — deve ficar aqui no topo para o IDE gerar
//    protótipos corretos ──────────────────────────────────
struct ServoTimer {
    gpio_num_t         pin;
    volatile int       pulseUs;
    esp_timer_handle_t periodTimer;
    esp_timer_handle_t pulseTimer;
};

static ServoTimer servos[3]; // [0]=aileron  [1]=leme  [2]=profundor

BNO080 myIMU;

SFE_UBLOX_GNSS myGPS;

HardwareSerial GPSSerial(2); // Usa a UART2 do ESP32-S3

// ════════════════════════════════════════════════════════
// ESC — igual ao original
// ════════════════════════════════════════════════════════
volatile int      escPulseUs    = PWM_MIN;
volatile uint32_t ultimoCounter = 0;

esp_timer_handle_t periodTimer = nullptr; // dispara a cada 20ms
esp_timer_handle_t pulseTimer  = nullptr; // desliga o pino após escPulseUs

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
    pulseArgs.dispatch_method = ESP_TIMER_TASK;   // ← era ISR
    esp_timer_create(&pulseArgs, &pulseTimer);

    esp_timer_create_args_t periodArgs = {};
    periodArgs.callback        = periodCallback;
    periodArgs.name            = "esc_period";
    periodArgs.dispatch_method = ESP_TIMER_TASK;  // ← era ISR
    esp_timer_create(&periodArgs, &periodTimer);
    esp_timer_start_periodic(periodTimer, 20000);
}

void escWrite(int us) {
    escPulseUs = constrain(us, PWM_MIN, PWM_MAX);
}

// IMU SETUP
void imuSetup() {
  delay(1000);

  Serial.println("=== Configurando BNO080 via SPI ===");

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

void imuPrintValues() {
    if (myIMU.dataAvailable()) {
        float gx = myIMU.getGyroX();
        float gy = myIMU.getGyroY();
        float gz = myIMU.getGyroZ();

        float roll  = myIMU.getRoll()  * 180.0 / PI;
        float pitch = myIMU.getPitch() * 180.0 / PI;
        float yaw   = myIMU.getYaw()   * 180.0 / PI;

        // Serial.print(gx, 4); Serial.print(",");
        // Serial.print(gy, 4); Serial.print(",");
        // Serial.print(gz, 4); Serial.print(",");
        Serial.print(roll, 2); Serial.print(",");
        Serial.print(pitch, 2); Serial.print(",");
        Serial.println(yaw, 2);
  }
}

// GPS
void gpsSetup() {
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

void gpsPrintValues() {
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


// ════════════════════════════════════════════════════════
// SERVOS — mesmo padrão do ESC, sem LEDC/Servo.h
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

// ── Valores globais recebidos via rádio ───────────────────
volatile int motorValue   = 0;
volatile int aileronValue = SERVO_MID;
volatile int rudderValue  = SERVO_MID;
volatile int elevValue    = SERVO_MID;

// ═══════════════════════════════════════════════════════
// TASK DO RÁDIO — 100% no Core 0
// ═══════════════════════════════════════════════════════
void radioTask(void* param) {
    SPIClass spi(HSPI);
    RF24 radio(CE_PIN, CSN_PIN);
    struct Packet {
        uint16_t throttle;
        uint16_t aileron;
        uint16_t rudder;
        uint16_t elevator;
    };

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);
    spi.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&spi)) {
        Serial.println("[CORE0][ERRO] RF24 falhou");
    } else {
        radio.setPALevel(RF24_PA_MIN);
        radio.setDataRate(RF24_250KBPS);
        radio.setChannel(76);
        radio.openReadingPipe(1, address);
        radio.startListening();
        Serial.println("[CORE0] RF24 pronto");
    }

    radio.flush_rx();

    for (;;) {
        if (radio.available()) {
            Packet p;
            while (radio.available()) radio.read(&p, sizeof(p));  // mantém só o último
            motorValue   = constrain((int)p.throttle, PWM_MIN,       PWM_MAX);
            aileronValue = constrain((int)p.aileron,  PWM_MIN_SERVO,  PWM_MAX_SERVO);
            rudderValue  = constrain((int)p.rudder,   PWM_MIN_SERVO,  PWM_MAX_SERVO);
            elevValue    = constrain((int)p.elevator, PWM_MIN_SERVO,  PWM_MAX_SERVO);
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void aguardarEnter(const char* msg) {
    Serial.println(msg);
    while (!Serial.available()) delay(50);
    while (Serial.available()) Serial.read();
}

// ═══════════════════════════════════════════════════════
// SETUP — Core 1
// ═══════════════════════════════════════════════════════
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("1 - Serial OK");

    // ESC — Sem LEDC, sem Servo.h, sem alocação de timer — zero conflito
    escSetup();
    escWrite(PWM_MIN);
    Serial.println("2b - ESC OK (1000us ativo)");

    // Servos — mesmo padrão do ESC
    servoSetup(servos[0], SERVO_AILERON_GPIO,  SERVO_MID, "srv0_pulse", "srv0_period");
    servoSetup(servos[1], SERVO_RUDDER_GPIO,   SERVO_MID, "srv1_pulse", "srv1_period");
    servoSetup(servos[2], SERVO_ELEVATOR_GPIO, SERVO_MID, "srv2_pulse", "srv2_period");
    Serial.println("3 - Servos OK (1500us centrado)");

    Serial.println("\n  [a] Apenas armar");
    // while (!Serial.available()) delay(50);
    // char opcao = Serial.read();
    // while (Serial.available()) Serial.read();

    // if (opcao == 'c' || opcao == 'C') {
    //     escWrite(PWM_MAX);
    //     aguardarEnter("[1] MAX carregado. DESCONECTE a bateria. ENTER quando feito.");
    //     aguardarEnter("[2] RECONECTE. Aguarde os bips. ENTER quando ouvir.");
    //     escWrite(PWM_MIN);
    //     Serial.println("[3] MIN enviado. Aguardando confirmacao...");
    //     delay(4000);
    //     Serial.println("✅ Calibrado!");
    // } else {
        delay(200);
        escWrite(PWM_MIN);
        Serial.println("[ARM] Aguardando boot ESC (5s)...");
        delay(5000);
        Serial.println("✅ ESC armado!");
    // }

    // RF24 isolado no Core 0 — Wire (I2C) só é acessado do Core 1, sem conflito
    xTaskCreatePinnedToCore(radioTask, "Radio", 10000, NULL, 1, NULL, 0);
    Serial.println("[CORE0] Radio iniciando...");
    Serial.println("Pronto!\n");

    imuSetup();
    gpsSetup();
}

// ═══════════════════════════════════════════════════════
// LOOP — Core 1, ESC + Servos + IMU
//
// IMU fica aqui (Core 1) por segurança:
//   Wire (I2C) não é thread-safe no ESP32 Arduino — manter
//   tudo I2C no mesmo core evita corrupção de dados.
// ═══════════════════════════════════════════════════════
void loop() {
    escWrite(motorValue);
    servoWrite(servos[0], aileronValue);  // Aileron   ← LeftX
    servoWrite(servos[1], rudderValue);   // Leme      ← RightX
    servoWrite(servos[2], elevValue);     // Profundor ← RightY
    gpsPrintValues();
}