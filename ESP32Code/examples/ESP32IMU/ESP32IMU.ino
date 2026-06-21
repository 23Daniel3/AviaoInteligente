#include <Wire.h>
#include <WiFi.h>
#include <SparkFun_BNO08x_Arduino_Library.h>
#include <ESP32Servo.h>

BNO08x myIMU; 
sh2_SensorValue_t sensorValue;

const char* ssid = "WIFI_ESP";
const char* password = "12345678";

// Servo
Servo servo;
const int servoPin = 13;
int lastServoPos = 90;

// Servidores
WiFiServer gyroServer(8080);
WiFiServer logServer(9090);
WiFiServer controlServer(10000);

WiFiClient gyroClient;
WiFiClient logClient;
WiFiClient controlClient;

unsigned long lastDataTime = 0;

void sendLog(const char* msg) {
  if (logClient && logClient.connected()) logClient.println(msg);
  Serial.println(msg);
}

void sendGyro(float roll, float pitch, float yaw) {
  if (gyroClient && gyroClient.connected()) {
    gyroClient.printf("%f,%f,%f\n", roll, pitch, yaw);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(17,18);

  // Servo
  servo.attach(servoPin, 600, 2400);
  servo.write(90);

  // Wi-Fi
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  Serial.print("IP do ESP32: "); Serial.println(WiFi.softAPIP());
  gyroServer.begin();
  logServer.begin();
  controlServer.begin();

  // IMU
  if (!myIMU.begin(BNO08x_DEFAULT_ADDRESS, Wire)) {
    sendLog("❌ Erro iniciando BNO085, tentando novamente...");
    delay(2000);
    return;
  } else {
    sendLog("✅ BNO085 iniciado");
    myIMU.enableRotationVector(100);
  }
}

void loop() {
  if (!gyroClient || !gyroClient.connected()) gyroClient = gyroServer.available();
  if (!logClient || !logClient.connected()) logClient = logServer.available();
  if (!controlClient || !controlClient.connected()) controlClient = controlServer.available();

  // IMU -> Dashboard
  if (myIMU.getSensorEvent()) {
    float roll  = myIMU.getRoll()  * 180.0f / PI;
    float pitch = myIMU.getPitch() * 180.0f / PI;
    float yaw   = myIMU.getYaw()   * 180.0f / PI;
    sendGyro(roll, pitch, yaw);
  }

  // Controle vindo da Dashboard
  if (controlClient && controlClient.connected() && controlClient.available()) {
    String data = controlClient.readStringUntil('\n');
    data.trim();
    if (data.length() > 0) {
      float val = data.toFloat();
      val = constrain(val, -1.0, 1.0);

      // Mapeamento direto em pulsos
      int pulse = map(val * 100, -100, 100, 600, 2400);
      servo.writeMicroseconds(pulse);

      lastServoPos = pulse;
      lastDataTime = millis();
      sendLog(("🎮 Servo pulse: " + String(pulse)).c_str());
    }
  }

  // Timeout: volta pro centro se perder dados
  if (millis() - lastDataTime > 1000) {
    servo.write(90);
  }
}
