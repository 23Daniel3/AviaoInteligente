#include <WiFi.h>
#include <WebSocketsServer.h>

const char* ssid = "ESP32-LED";   // Nome da rede Wi-Fi criada pelo ESP32
const char* password = "123456789"; // Senha da rede Wi-Fi
const int ledPin = 4; // Pino do LED (D4)

WebSocketsServer webSocket = WebSocketsServer(81);

void handleWebSocketMessage(uint8_t num, uint8_t *payload, size_t length) {
    String message = String((char*)payload).substring(0, length);
    
    if (message == "acender") {
        digitalWrite(ledPin, HIGH); // Acende o LED
    } else if (message == "apagar") {
        digitalWrite(ledPin, LOW); // Apaga o LED
    }
}

void setup() {
    Serial.begin(115200);  // Inicializa a comunicação serial
    pinMode(ledPin, OUTPUT); // Configura o pino do LED como saída

    // Cria a rede Wi-Fi do ESP32 (Access Point)
    WiFi.softAP(ssid, password); 
    Serial.print("IP da rede criada: ");
    Serial.println(WiFi.softAPIP()); // Exibe o IP do ESP32 na rede criada

    // Configura o servidor WebSocket
    webSocket.begin();
    webSocket.onEvent([](uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
        if (type == WStype_TEXT) {
            handleWebSocketMessage(num, payload, length);
        }
    });
}

void loop() {
    webSocket.loop(); // Mantém o WebSocket funcionando
}
