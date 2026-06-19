#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>
#include "driver/gpio.h"
#include "esp_timer.h"

// ── Pinos ────────────────────────────────────────────────────────────
constexpr gpio_num_t ESC_GPIO  = GPIO_NUM_18;
// constexpr gpio_num_t SRV1_GPIO = GPIO_NUM_XX;  // Servo 1 — escolha o pino

constexpr uint8_t CE_PIN   = 4;
constexpr uint8_t CSN_PIN  = 5;
constexpr uint8_t SCK_PIN  = 12;
constexpr uint8_t MISO_PIN = 13;
constexpr uint8_t MOSI_PIN = 11;

constexpr int PWM_MIN = 1000;
constexpr int PWM_MAX = 2000;
const uint8_t address[6] = "NODE1";

// ── Pacote (espelho exato do transmissor) ────────────────────────────
struct Packet {
    bool     motorEnabled;
    uint16_t throttle;
    // uint16_t servo1;
};

// ── Estado compartilhado Core 0 → Core 1 ────────────────────────────
volatile bool motorEnabled = false;
volatile int  escPulseUs   = PWM_MIN;
// volatile int  srv1PulseUs  = 1500;

// ── PWM por timer — ESC ──────────────────────────────────────────────
esp_timer_handle_t escPulseTimer  = nullptr;
esp_timer_handle_t escPeriodTimer = nullptr;

void escPulseEnd(void*) { gpio_set_level(ESC_GPIO, 0); }
void escPeriod(void*)   {
    gpio_set_level(ESC_GPIO, 1);
    esp_timer_start_once(escPulseTimer, escPulseUs);
}

// ── PWM por timer — Servo 1 (template para copiar) ───────────────────
// esp_timer_handle_t srv1PulseTimer  = nullptr;
// esp_timer_handle_t srv1PeriodTimer = nullptr;
//
// void srv1PulseEnd(void*) { gpio_set_level(SRV1_GPIO, 0); }
// void srv1Period(void*)   {
//     gpio_set_level(SRV1_GPIO, 1);
//     esp_timer_start_once(srv1PulseTimer, srv1PulseUs);
// }

void escSetup() {
    gpio_config_t cfg = {};
    cfg.mode         = GPIO_MODE_OUTPUT;
    cfg.pin_bit_mask = (1ULL << ESC_GPIO);
    gpio_config(&cfg);
    gpio_set_level(ESC_GPIO, 0);

    esp_timer_create_args_t pa = {};
    pa.callback        = escPulseEnd;
    pa.name            = "esc_pulse";
    pa.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&pa, &escPulseTimer);

    esp_timer_create_args_t pb = {};
    pb.callback        = escPeriod;
    pb.name            = "esc_period";
    pb.dispatch_method = ESP_TIMER_TASK;
    esp_timer_create(&pb, &escPeriodTimer);
    esp_timer_start_periodic(escPeriodTimer, 20000); // 50 Hz
}

// void srv1Setup() {
//     gpio_config_t cfg = {};
//     cfg.mode         = GPIO_MODE_OUTPUT;
//     cfg.pin_bit_mask = (1ULL << SRV1_GPIO);
//     gpio_config(&cfg);
//     gpio_set_level(SRV1_GPIO, 0);
//
//     esp_timer_create_args_t pa = {};
//     pa.callback = srv1PulseEnd; pa.name = "srv1_pulse";
//     pa.dispatch_method = ESP_TIMER_TASK;
//     esp_timer_create(&pa, &srv1PulseTimer);
//
//     esp_timer_create_args_t pb = {};
//     pb.callback = srv1Period; pb.name = "srv1_period";
//     pb.dispatch_method = ESP_TIMER_TASK;
//     esp_timer_create(&pb, &srv1PeriodTimer);
//     esp_timer_start_periodic(srv1PeriodTimer, 20000);
// }

void escWrite(int us) { escPulseUs = constrain(us, PWM_MIN, PWM_MAX); }

// ── Task do Rádio — Core 0 ───────────────────────────────────────────
void radioTask(void* param) {
    SPIClass spi(FSPI);
    RF24 radio(CE_PIN, CSN_PIN);

    pinMode(CE_PIN,  OUTPUT); digitalWrite(CE_PIN,  LOW);
    pinMode(CSN_PIN, OUTPUT); digitalWrite(CSN_PIN, HIGH);
    spi.begin(SCK_PIN, MISO_PIN, MOSI_PIN);

    if (!radio.begin(&spi)) {
        Serial.println("[CORE0][ERRO] RF24 falhou");
    } else {
        radio.setPALevel(RF24_PA_LOW);
        radio.setDataRate(RF24_250KBPS);
        radio.setChannel(76);
        radio.openReadingPipe(1, address);
        radio.startListening();
        Serial.println("[CORE0] RF24 pronto");
    }

    for (;;) {
        if (radio.available()) {
            Packet p;
            while (radio.available()) radio.read(&p, sizeof(p));

            motorEnabled = p.motorEnabled;
            escPulseUs   = p.motorEnabled
                             ? constrain((int)p.throttle, PWM_MIN, PWM_MAX)
                             : PWM_MIN;
            // srv1PulseUs = constrain((int)p.servo1, PWM_MIN, PWM_MAX);
        }
        vTaskDelay(2 / portTICK_PERIOD_MS);
    }
}

void aguardarEnter(const char* msg) {
    Serial.println(msg);
    while (!Serial.available()) delay(50);
    while (Serial.available()) Serial.read();
}

// ── Setup — Core 1 ───────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("1 - Serial OK");

    escSetup();
    // srv1Setup(); // descomentar para ativar Servo 1
    escWrite(PWM_MIN);
    Serial.println("2 - ESC OK (1000us ativo)");

    Serial.println("\n  [c] Calibrar ESC");
    Serial.println("  [a] Apenas armar");
    while (!Serial.available()) delay(50);
    char opcao = Serial.read();
    while (Serial.available()) Serial.read();

    if (opcao == 'c' || opcao == 'C') {
        escWrite(PWM_MAX);
        aguardarEnter("[1] MAX carregado. DESCONECTE a bateria. ENTER quando feito.");
        aguardarEnter("[2] RECONECTE. Aguarde os bips. ENTER quando ouvir.");
        escWrite(PWM_MIN);
        Serial.println("[3] MIN enviado. Aguardando confirmacao...");
        delay(4000);
        Serial.println("Calibrado!");
    } else {
        escWrite(PWM_MIN);
        Serial.println("[ARM] Aguardando boot ESC (5s)...");
        delay(5000);
        Serial.println("ESC armado!");
    }

    xTaskCreatePinnedToCore(radioTask, "Radio", 10000, NULL, 1, NULL, 0);
    Serial.println("Sistema pronto. Motor controlado via RF24.");
}

// ── Loop — Core 1 ────────────────────────────────────────────────────
void loop() {
    // radioTask (Core 0) atualiza escPulseUs continuamente.
    // Aqui só garantimos segurança: motor vai a zero se desativado.
    if (!motorEnabled) {
        escWrite(PWM_MIN);
    }
    delay(20);
}