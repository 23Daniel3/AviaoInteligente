#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>
#include "driver/gpio.h"
#include "esp_timer.h"

constexpr gpio_num_t ESC_GPIO = GPIO_NUM_18;
constexpr uint8_t CE_PIN   = 4;
constexpr uint8_t CSN_PIN  = 5;
constexpr uint8_t SCK_PIN  = 12;
constexpr uint8_t MISO_PIN = 13;
constexpr uint8_t MOSI_PIN = 11;
constexpr int     PWM_MIN  = 1000;
constexpr int     PWM_MAX  = 2000;
const uint8_t     address[6] = "NODE1";

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
    // GPIO
    gpio_config_t cfg = {};
    cfg.mode         = GPIO_MODE_OUTPUT;
    cfg.pin_bit_mask = (1ULL << ESC_GPIO);
    gpio_config(&cfg);
    gpio_set_level(ESC_GPIO, 0);

    // Timer: fim do pulso
    esp_timer_create_args_t pulseArgs = {};
    pulseArgs.callback         = pulseEndCallback;
    pulseArgs.name             = "esc_pulse";
    pulseArgs.dispatch_method  = ESP_TIMER_TASK;   // ← era ISR
    esp_timer_create(&pulseArgs, &pulseTimer);

    // Timer: período 50Hz = 20000us
    esp_timer_create_args_t periodArgs = {};
    periodArgs.callback        = periodCallback;
    periodArgs.name            = "esc_period";
    periodArgs.dispatch_method = ESP_TIMER_TASK;   // ← era ISR
    esp_timer_create(&periodArgs, &periodTimer);
    esp_timer_start_periodic(periodTimer, 20000);
}

void escWrite(int us) {
    escPulseUs = constrain(us, PWM_MIN, PWM_MAX);
}

int motorValue = 0;

// ═══════════════════════════════════════════════════════
// TASK DO RÁDIO — 100% no Core 0
// ═══════════════════════════════════════════════════════
void radioTask(void* param) {
    SPIClass spi(FSPI);
    RF24 radio(CE_PIN, CSN_PIN);
    struct Packet { uint16_t throttle; };

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
    
    radio.flush_rx();
    
    for (;;) {
        if (radio.available()) {
            Packet p;
            while (radio.available()) radio.read(&p, sizeof(p));  // mantém só o último
            motorValue = constrain((int)p.throttle, PWM_MIN, PWM_MAX);
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

    // Sem LEDC, sem Servo.h, sem alocação de timer — zero conflito
    escSetup();
    escWrite(PWM_MIN);
    Serial.println("2 - ESC OK (1000us ativo)");

    Serial.println("\n  [c] Calibrar ESC");
    Serial.println("  [a] Apenas armar");
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

    // RF24 só sobe depois do ESC armado, isolado no Core 0
    xTaskCreatePinnedToCore(radioTask, "Radio", 10000, NULL, 1, NULL, 0);
    Serial.println("[CORE0] Radio iniciando...");
    Serial.println("Envie valores 1000-2000:\n");
}

// ═══════════════════════════════════════════════════════
// LOOP — Core 1, só ESC
// ═══════════════════════════════════════════════════════
void loop() {
    // if (Serial.available() > 0) {
    //     String entrada = Serial.readStringUntil('\n');
    //     entrada.trim();
    //     int valor = entrada.toInt();

    //     if (valor >= PWM_MIN && valor <= PWM_MAX) {
    //         escWrite(valor);
    //         Serial.printf("[ESC] → %d us\n", valor);
    //     } else if (entrada.length() > 0) {
    //         Serial.println("[ERRO] Use 1000-2000");
    //     }
    // }

    escWrite(motorValue);
}